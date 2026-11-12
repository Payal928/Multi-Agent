
from flask import Flask, render_template, request, jsonify
from multi_agent import graph

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():

    try:
        data = request.get_json()

        user_query = data.get("message", "").strip()

        if not user_query:
            return jsonify({
                "error": "Please enter a question."
            }), 400

        # Initial LangGraph state
        initial_state = {
            "user_query": user_query,
            "clean_query": None,
            "is_blocked": False,
            "selected_agent": None,
            "final_response": None,
            "pii_detected": False,
            "guardrail_events": [],
            "blocked_reason": None
        }

        # Run the complete LangGraph workflow
        result = graph.invoke(initial_state)

        return jsonify({
            "success": True,
            "answer": result.get("final_response"),
            "selected_agent": result.get("selected_agent"),
            "is_blocked": result.get("is_blocked", False),
            "pii_detected": result.get("pii_detected", False),
            "guardrail_events": result.get("guardrail_events", []),
            "blocked_reason": result.get("blocked_reason")
        })

    except Exception as e:

        print("Flask Error:", str(e))

        return jsonify({
            "success": False,
            "error": "Something went wrong while processing your request."
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
