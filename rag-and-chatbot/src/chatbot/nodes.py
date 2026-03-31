"""Node functions for LangGraph chatbot."""

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



def router_node(state: GraphState) -> GraphState:
    """Classify user intent: question, reservation, or status_check."""
    llm = _get_llm()

    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

    reservation_data = state.get("reservation_data", {})
    if reservation_data:
        # Check if any reservation field exists but not all required fields are complete
        has_some_data = any([
            reservation_data.get("start_time"),
            reservation_data.get("end_time"),
            reservation_data.get("name"),
            reservation_data.get("car_number")
        ])

        # Check if all required fields are NOT complete
        required_fields = ["name", "car_number", "start_time", "end_time", "preferred_spot_type"]
        is_incomplete = not all(reservation_data.get(field) for field in required_fields)

        # If we have some data but it's incomplete, continue the reservation flow
        if has_some_data and is_incomplete:
            return {
                **state,
                "intent": "reservation",
                "next_action": "route_to_handler"
            }

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

"status_check" - User wants to:
  - Check their reservation status
  - Query about their booking
  - Find out if reservation was approved/rejected
  - Examples: "what's my status?", "check my reservation", "was my booking approved?"

User message: "{user_input}"

Respond with ONLY one word: either "question", "reservation", or "status_check"
"""

    response = llm.invoke([SystemMessage(content=classification_prompt)])
    intent = response.content.strip().lower()

    if intent not in ["question", "reservation", "status_check"]:
        intent = "question"  # Default to question if unclear

    return {
        **state,
        "intent": intent,
        "next_action": "route_to_handler"
    }



def rag_node(state: GraphState) -> GraphState:
    """Answer questions using RAG with real-time availability checks when needed."""
    llm = _get_llm()
    retriever = _get_compression_retriever()

    last_message = state["messages"][-1]
    query = last_message.content if hasattr(last_message, 'content') else str(last_message)

    is_safe, reason = validate_query(query)
    if not is_safe:
        error_response = f"I'm sorry, but I cannot process that request. {reason}. Please rephrase your question."
        updated_messages = state["messages"] + [AIMessage(content=error_response)]
        return {
            **state,
            "messages": updated_messages,
            "next_action": "wait_for_user"
        }

    docs = retriever.invoke(query)

    context = "\n\n".join([doc.page_content for doc in docs])

    availability_check_prompt = f"""Does this question ask about current availability, free spots, or if spaces are available right now?

Question: "{query}"

Respond with ONLY "yes" or "no"."""

    availability_response = llm.invoke([SystemMessage(content=availability_check_prompt)])
    is_availability_query = availability_response.content.strip().lower() == "yes"

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

    rag_prompt = f"""You are a helpful parking facility assistant. Answer the user's question based on the provided information.

Policy Context:
{context}
{realtime_data}

User Question: {query}

Provide a helpful, concise answer. Combine policy information with real-time availability when relevant.
If the information is not in the context, say so politely.
"""

    response = llm.invoke([HumanMessage(content=rag_prompt)])

    filtered_response = apply_guardrails(response.content, user_context=state.get("reservation_data", {}))

    updated_messages = state["messages"] + [AIMessage(content=filtered_response)]

    return {
        **state,
        "messages": updated_messages,
        "next_action": "wait_for_user"
    }



def _check_parking_availability(start_time: str, end_time: str) -> Dict[str, Any]:
    """Check spot availability excluding time conflicts with existing reservations."""
    db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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



def reservation_collector_node(state: GraphState) -> GraphState:
    """Collect reservation details: times, availability, name, car number, spot type."""
    llm = _get_llm()
    reservation_data = state.get("reservation_data", {})

    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

    current_datetime = datetime.now()

    # Build context about what we already have and what we're asking for
    already_collected = []
    currently_asking_for = None

    if reservation_data.get("start_time"):
        already_collected.append(f"start_time: {reservation_data['start_time']}")
    else:
        currently_asking_for = "start_time"

    if reservation_data.get("end_time"):
        already_collected.append(f"end_time: {reservation_data['end_time']}")
    elif currently_asking_for is None:
        currently_asking_for = "end_time"

    if reservation_data.get("name"):
        already_collected.append(f"name: {reservation_data['name']}")
    elif currently_asking_for is None:
        currently_asking_for = "name"

    if reservation_data.get("car_number"):
        already_collected.append(f"car_number: {reservation_data['car_number']}")
    elif currently_asking_for is None:
        currently_asking_for = "car_number"

    if reservation_data.get("preferred_spot_type"):
        already_collected.append(f"preferred_spot_type: {reservation_data['preferred_spot_type']}")
    elif currently_asking_for is None:
        currently_asking_for = "preferred_spot_type"

    already_collected_str = "\n".join(already_collected) if already_collected else "None yet"

    extraction_prompt = f"""You are helping collect parking reservation information.

ALREADY COLLECTED (DO NOT extract these again):
{already_collected_str}

CURRENTLY ASKING USER FOR: {currently_asking_for}

User's latest message: "{user_input}"
Current date and time: {current_datetime}

IMPORTANT: Only extract NEW information that is NOT already collected. Do not overwrite existing fields.

Extract ONLY the following if present in the user's message:
- name: Full name (first and last)
- car_number: License plate number
- start_time: When they want to start parking (date and time)
- end_time: When they want to leave (date and time)
- preferred_spot_type: Parking spot type preference (must be exactly one of: "Standard", "EV", or "Accessible")

Respond in this exact format:
name: [extracted name or "none"]
car_number: [extracted car number or "none"]
start_time: [extracted start time or "none"]
end_time: [extracted end time or "none"]
preferred_spot_type: [extracted spot type (Standard/EV/Accessible) or "none"]
"""

    extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])

    # Only update fields that aren't already set
    for line in extraction_response.content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Only store if the field is empty and the value is not "none"
            if value.lower() != "none" and key in ["name", "car_number", "start_time", "end_time", "preferred_spot_type"]:
                if not reservation_data.get(key):  # Only set if not already set
                    reservation_data[key] = value


    if not reservation_data.get("start_time"):
        response_text = "I'd be happy to help you with a parking reservation! When would you like to start parking? (Please provide date and time)"

    elif not reservation_data.get("end_time"):
        response_text = "Great! And when do you plan to leave? (Please provide date and time)"

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

 Time Slot: {reservation_data['start_time']} to {reservation_data['end_time']}
 Available Spots:
{availability_summary}

To complete your pre-reservation, I'll need a few more details.

What is your full name?"""

            # Store availability info for later use
            reservation_data["available_spots"] = availability["spots"]
            reservation_data["count_by_type"] = availability["count_by_type"]

    elif not reservation_data.get("name"):
        response_text = "What is your full name?"

    elif not reservation_data.get("car_number"):
        response_text = f"Thank you, {reservation_data['name']}! What is your vehicle's license plate number?"

    elif not reservation_data.get("preferred_spot_type"):
        # Get available spot types from count_by_type
        count_by_type = reservation_data.get("count_by_type", {})
        if count_by_type:
            spot_options = "\n".join([
                f"  • {spot_type}: {count} available"
                for spot_type, count in count_by_type.items()
            ])
            response_text = f"""Great! We have the following spot types available:

{spot_options}

Which type would you prefer? (Please choose: Standard, EV, or Accessible)"""
        else:
            # Fallback if somehow count_by_type is missing
            response_text = "Which spot type would you prefer: Standard, EV, or Accessible?"

    else:
        # Get the preferred spot type name for display
        preferred_type = reservation_data.get("preferred_spot_type", "Your preferred")

        response_text = f"""Perfect! I have collected all the information for your pre-reservation:

 Pre-Reservation Details:

 Name: {reservation_data['name']}
 License Plate: {reservation_data['car_number']}
 Start Time: {reservation_data['start_time']}
 End Time: {reservation_data['end_time']}
  Preferred Spot Type: {preferred_type}

Your information has been collected. Processing your reservation..."""

    updated_messages = state["messages"] + [AIMessage(content=response_text)]

    return {
        **state,
        "messages": updated_messages,
        "reservation_data": reservation_data,
        "next_action": "wait_for_user"
    }



def create_reservation_node(state: GraphState) -> GraphState:
    """Create pending reservation in database and assign preferred spot."""
    reservation_data = state["reservation_data"]

    available_spots = reservation_data["available_spots"]
    preferred_type = reservation_data.get("preferred_spot_type", "Standard")

    selected_spot = next(
        (spot for spot in available_spots if spot["type"] == preferred_type),
        available_spots[0] if available_spots else None
    )

    if not selected_spot:
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content="Error: No available spots found. Please try again.")],
            "next_action": "wait_for_user"
        }

    db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    thread_id = state.get("thread_id")

    try:
        cursor.execute("""
            INSERT INTO reservations
            (spot_id, user_name, car_number, start_time, end_time, status, thread_id)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (
            selected_spot["id"],
            reservation_data["name"],
            reservation_data["car_number"],
            reservation_data["start_time"],
            reservation_data["end_time"],
            thread_id
        ))
        conn.commit()

        reservation_id = cursor.lastrowid

    finally:
        conn.close()

    updated_reservation_data = {
        **reservation_data,
        "reservation_id": reservation_id,
        "assigned_spot_id": selected_spot["id"],
        "status": "pending"
    }

    response_text = f"""Reservation created successfully!

Reservation ID: #{reservation_id}
Assigned Spot: {selected_spot["number"]} ({selected_spot["type"]})
Floor: {selected_spot["floor"]}

Your reservation has been submitted and is pending admin approval.
I'll continue to assist you with any other questions!
You can check your reservation status anytime by asking: "What's my reservation status?"
"""

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response_text)],
        "reservation_data": updated_reservation_data,
        "next_action": "wait_for_user"
    }


def status_checker_node(state: GraphState) -> GraphState:
    """Query and display user's most recent reservation status."""
    reservation_data = state.get("reservation_data", {})
    name = reservation_data.get("name")
    car_number = reservation_data.get("car_number")

    if not name and not car_number:
        last_message = state["messages"][-1]
        user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

        # Use LLM to extract name or car number if provided
        llm = _get_llm()
        extraction_prompt = f"""Extract name or license plate number from this query if present:
"{user_input}"

Respond in format:
name: [name or "none"]
car_number: [license plate or "none"]
"""
        extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])

        for line in extraction_response.content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if value.lower() != "none" and key == "name":
                    name = value
                elif value.lower() != "none" and key == "car_number":
                    car_number = value

    if not name and not car_number:
        response_text = """I don't have your reservation details in this conversation.
Could you provide your name or license plate number so I can look up your reservation?

For example: "Check status for John Smith" or "My plate is ABC-1234"
"""
    else:
        db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Find most recent reservation for this user
            cursor.execute("""
                SELECT
                    r.id,
                    r.status,
                    r.start_time,
                    r.end_time,
                    ps.spot_number,
                    ps.spot_type,
                    ps.floor,
                    r.reservation_time
                FROM reservations r
                JOIN parking_spots ps ON r.spot_id = ps.id
                WHERE r.user_name = ? OR r.car_number = ?
                ORDER BY r.reservation_time DESC
                LIMIT 1
            """, (name or "", car_number or ""))

            result = cursor.fetchone()

        finally:
            conn.close()

        if not result:
            response_text = f"""I couldn't find any reservations for {name or car_number}.

If you recently made a reservation, please make sure the name or license plate matches exactly.
"""
        else:
            res_id, status, start, end, spot_num, spot_type, floor, reserved_at = result

            response_text = f"""Reservation Status

 Reservation ID: #{res_id}
 Status: {status.upper()}
  Assigned Spot: {spot_num} ({spot_type})
 Floor: {floor}
 Start: {start}
 End: {end}
 Reserved: {reserved_at}
"""

            if status == "approved":
                response_text += "\n Your reservation has been approved! See you soon."
            elif status == "rejected":
                response_text += "\n Unfortunately, your reservation was not approved. Please contact us for assistance."
            else:
                response_text += "\n Your reservation is awaiting admin approval. We'll process it shortly."

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response_text)],
        "next_action": "wait_for_user"
    }


