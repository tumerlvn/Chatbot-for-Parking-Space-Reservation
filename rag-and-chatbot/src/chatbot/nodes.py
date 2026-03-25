"""
Node Functions for the LangGraph Chatbot
Each node is a function that takes GraphState and returns updated GraphState
"""

import os
import sqlite3
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from .state import GraphState
from .guardrails import apply_guardrails, validate_query


# ============================================================================
# Global Setup - Initialize retrieval components (lazy loaded)
# ============================================================================

_vector_store = None
_compression_retriever = None
_llm = None


def _get_vector_store():
    """Lazy load Milvus vector store"""
    global _vector_store
    if _vector_store is None:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        URI = os.path.join(os.path.dirname(__file__), "../../data/parking.db")
        _vector_store = Milvus(
            embedding_function=embeddings,
            connection_args={"uri": URI},
            collection_name="parking_policy_collection",
            drop_old=False
        )
    return _vector_store


def _get_compression_retriever():
    """Lazy load the reranking retriever"""
    global _compression_retriever
    if _compression_retriever is None:
        vector_store = _get_vector_store()
        base_retriever = vector_store.as_retriever(search_kwargs={"k": 10})

        reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        compressor = CrossEncoderReranker(model=reranker_model, top_n=3)

        _compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever
        )
    return _compression_retriever


def _get_llm():
    """Lazy load OpenAI LLM"""
    global _llm
    if _llm is None:
        # _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        _llm = AzureChatOpenAI(model_name="gpt-4o-mini-2024-07-18")
    return _llm


# ============================================================================
# Node 1: Router - Classifies user intent
# ============================================================================

def router_node(state: GraphState) -> GraphState:
    """
    Analyzes the user's latest message and classifies intent.

    Returns:
        Updated state with 'intent' set to 'question' or 'reservation'
    """
    llm = _get_llm()

    # Get the last user message
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

    # Use LLM to classify intent
    classification_prompt = f"""You are an intent classifier for a parking reservation chatbot.

Analyze the user's message and classify it into ONE of these intents:

"question" - User is asking about:
  - Parking policies, rules, prices, amenities
  - Operating hours, location, access
  - Availability ("are spots free?", "do you have EV charging?")
  - General information

"reservation" - User wants to:
  - Make a booking/reservation
  - Provide booking details (name, car number, times)
  - Continue an ongoing reservation process

User message: "{user_input}"

Respond with ONLY one word: either "question" or "reservation"
"""

    response = llm.invoke([SystemMessage(content=classification_prompt)])
    intent = response.content.strip().lower()

    # Validate intent
    if intent not in ["question", "reservation"]:
        intent = "question"  # Default to question if unclear

    return {
        **state,
        "intent": intent,
        "next_action": "route_to_handler"
    }


# ============================================================================
# Node 2: RAG Node - Answers policy questions
# ============================================================================

def rag_node(state: GraphState) -> GraphState:
    """
    Retrieves relevant policy information and generates an answer.

    Uses Milvus vector store + reranker to find relevant context,
    then uses LLM to generate a natural language answer.

    Enhancement: Also checks SQLite for real-time availability when needed.
    """
    llm = _get_llm()
    retriever = _get_compression_retriever()

    # Get the user's question
    last_message = state["messages"][-1]
    query = last_message.content if hasattr(last_message, 'content') else str(last_message)

    # GUARD RAILS: Validate user query for injection attempts
    is_safe, reason = validate_query(query)
    if not is_safe:
        error_response = f"I'm sorry, but I cannot process that request. {reason}. Please rephrase your question."
        updated_messages = state["messages"] + [AIMessage(content=error_response)]
        return {
            **state,
            "messages": updated_messages,
            "next_action": "wait_for_user"
        }

    # Retrieve relevant documents from vector store
    docs = retriever.invoke(query)

    # Build context from retrieved documents
    context = "\n\n".join([doc.page_content for doc in docs])

    # Check if query is about availability using LLM
    availability_check_prompt = f"""Does this question ask about current availability, free spots, or if spaces are available right now?

Question: "{query}"

Respond with ONLY "yes" or "no"."""

    availability_response = llm.invoke([SystemMessage(content=availability_check_prompt)])
    is_availability_query = availability_response.content.strip().lower() == "yes"

    # If asking about availability, get real-time data from SQLite
    realtime_data = ""
    if is_availability_query:
        db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT spot_type, COUNT(*) as available_count
            FROM parking_spots
            WHERE status = 'available'
            GROUP BY spot_type
        """)

        availability = cursor.fetchall()
        conn.close()

        if availability:
            realtime_data = "\n\nCurrent Real-Time Availability:\n"
            for spot_type, count in availability:
                realtime_data += f"- {spot_type}: {count} spot(s) available\n"
        else:
            realtime_data = "\n\nCurrent Real-Time Availability: No spots currently available."

    # Generate answer using LLM with both policy and real-time data
    rag_prompt = f"""You are a helpful parking facility assistant. Answer the user's question based on the provided information.

Policy Context:
{context}
{realtime_data}

User Question: {query}

Provide a helpful, concise answer. Combine policy information with real-time availability when relevant.
If the information is not in the context, say so politely.
"""

    response = llm.invoke([HumanMessage(content=rag_prompt)])

    # GUARD RAILS: Filter response for sensitive data
    filtered_response = apply_guardrails(response.content, user_context=state.get("reservation_data", {}))

    # Add AI response to messages
    updated_messages = state["messages"] + [AIMessage(content=filtered_response)]

    return {
        **state,
        "messages": updated_messages,
        "next_action": "wait_for_user"
    }


# ============================================================================
# Helper Function: Check Availability
# ============================================================================

def _check_parking_availability(start_time: str, end_time: str) -> Dict[str, Any]:
    """
    Check parking spot availability for the given time range with time conflict detection.

    Checks:
    1. Spots with status='available'
    2. Excludes spots that have conflicting reservations in the time range

    Time conflict logic:
    A reservation conflicts if:
    - (reservation_start <= requested_end AND reservation_end >= requested_start)

    Returns:
        Dict with:
        - available: bool
        - spots: list of available spots
        - count_by_type: dict with counts by spot type
        - total_count: total available spots
    """
    db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query: Get spots that are:
    # 1. status='available'
    # 2. NOT in reservations table with conflicting times (status != 'cancelled')
    cursor.execute("""
        SELECT
            ps.id,
            ps.spot_number,
            ps.spot_type,
            ps.floor,
            ps.price_per_hour
        FROM parking_spots ps
        WHERE ps.status = 'available'
        AND ps.id NOT IN (
            SELECT spot_id
            FROM reservations
            WHERE status != 'cancelled'
            AND (
                (start_time <= ? AND end_time >= ?)
                OR (start_time <= ? AND end_time >= ?)
                OR (start_time >= ? AND end_time <= ?)
            )
        )
        ORDER BY ps.spot_type, ps.floor
    """, (end_time, start_time, end_time, end_time, start_time, end_time))

    available_spots = cursor.fetchall()
    conn.close()

    # Group by type
    count_by_type = {}
    spots_list = []

    for spot in available_spots:
        spot_id, spot_number, spot_type, floor, price = spot
        spots_list.append({
            "id": spot_id,
            "number": spot_number,
            "type": spot_type,
            "floor": floor,
            "price": price
        })
        count_by_type[spot_type] = count_by_type.get(spot_type, 0) + 1

    return {
        "available": len(available_spots) > 0,
        "spots": spots_list,
        "count_by_type": count_by_type,
        "total_count": len(available_spots)
    }


# ============================================================================
# Node 3: Reservation Collector - Gathers user information
# ============================================================================

def reservation_collector_node(state: GraphState) -> GraphState:
    """
    Collects reservation information step by step.

    Improved Flow (Stage 1 - Pre-reservation):
    1. Ask for start_time
    2. Ask for end_time
    3. Check availability → If none, suggest alternatives and stop
    4. Ask for name (only if spots available)
    5. Ask for car_number (only if spots available)
    6. Show summary → Ready for admin approval (Stage 2)
    """
    llm = _get_llm()
    reservation_data = state.get("reservation_data", {})

    # Get the user's latest message
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

    current_datetime = datetime.now()

    # Extract information from user input using LLM
    extraction_prompt = f"""You are helping collect parking reservation information.

Current reservation data: {reservation_data}
User's latest message: "{user_input}"

For context todays date and time is: {current_datetime}

Extract the following information if present in the user's message:
- name: Full name (first and last)
- car_number: License plate number
- start_time: When they want to start parking (date and time)
- end_time: When they want to leave (date and time)

Respond in this exact format:
name: [extracted name or "none"]
car_number: [extracted car number or "none"]
start_time: [extracted start time or "none"]
end_time: [extracted end time or "none"]
"""

    extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])

    # Parse extracted information
    for line in extraction_response.content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if value.lower() != "none" and key in ["name", "car_number", "start_time", "end_time"]:
                reservation_data[key] = value

    # NEW FLOW: Ask for times FIRST, then check availability, then personal info

    # Step 1: Ask for start time
    if not reservation_data.get("start_time"):
        response_text = "I'd be happy to help you with a parking reservation! When would you like to start parking? (Please provide date and time)"

    # Step 2: Ask for end time
    elif not reservation_data.get("end_time"):
        response_text = "Great! And when do you plan to leave? (Please provide date and time)"

    # Step 3: Check availability (after we have both times)
    elif not reservation_data.get("availability_checked"):
        availability = _check_parking_availability(
            reservation_data["start_time"],
            reservation_data["end_time"]
        )

        reservation_data["availability_checked"] = True

        if not availability["available"]:
            # No spots available - inform user and stop
            response_text = f"""I'm sorry, but there are no available parking spots for the requested time period ({reservation_data['start_time']} to {reservation_data['end_time']}).

Would you like to:
1. Try a different time period
2. Check availability for another day

You can also ask me about our operating hours and pricing."""

            # Reset times so user can try again
            reservation_data.pop("start_time", None)
            reservation_data.pop("end_time", None)
            reservation_data.pop("availability_checked", None)

        else:
            # Spots available! Show what's available and continue
            availability_summary = "\n".join([
                f"  • {spot_type}: {count} spot(s)"
                for spot_type, count in availability["count_by_type"].items()
            ])

            response_text = f"""Great news! We have parking spots available for your requested time:

📅 Time Slot: {reservation_data['start_time']} to {reservation_data['end_time']}
✅ Available Spots:
{availability_summary}

To complete your pre-reservation, I'll need a few more details.

What is your full name?"""

            # Store availability info for later use
            reservation_data["available_spots"] = availability["spots"]
            reservation_data["count_by_type"] = availability["count_by_type"]

    # Step 4: Ask for name (only after availability confirmed)
    elif not reservation_data.get("name"):
        response_text = "What is your full name?"

    # Step 5: Ask for car number (only after name)
    elif not reservation_data.get("car_number"):
        response_text = f"Thank you, {reservation_data['name']}! What is your vehicle's license plate number?"

    # Step 6: All information collected - show summary
    else:
        # Build summary of available spots from count_by_type
        if reservation_data.get("count_by_type"):
            spot_summary = "\n".join([
                f"  • {spot_type}: {count} spot(s)"
                for spot_type, count in reservation_data["count_by_type"].items()
            ])
            spot_info = f"\n✅ Available Spots:\n{spot_summary}\n"
        else:
            spot_info = ""

        response_text = f"""Perfect! I have collected all the information for your pre-reservation:

📋 Pre-Reservation Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Name: {reservation_data['name']}
🚗 License Plate: {reservation_data['car_number']}
📅 Start Time: {reservation_data['start_time']}
📅 End Time: {reservation_data['end_time']}{spot_info}
✅ Status: Awaiting Admin Approval

Your pre-reservation request has been recorded. In the next stage, this information will be sent to our admin team for review and confirmation. You will receive a confirmation once approved.

Is there anything else I can help you with?"""

    updated_messages = state["messages"] + [AIMessage(content=response_text)]

    return {
        **state,
        "messages": updated_messages,
        "reservation_data": reservation_data,
        "next_action": "wait_for_user"
    }


