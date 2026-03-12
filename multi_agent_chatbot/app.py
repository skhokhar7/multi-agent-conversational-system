import gradio as gr
from utils.logger import get_logger
from multi_agent_chatbot.main import (
    init_state,
    run_turn,
    extract_trace,
    extract_plan,
)

_logs = get_logger(__name__)

# ---------------------------------------------------------
# Chat handler
# ---------------------------------------------------------
def on_user_submit(message, chat_history, state):
    if not message:
        return "", chat_history, state, gr.update(), gr.update()

    # Add user message
    chat_history.append({"role": "user", "content": message})

    # Run backend
    assistant_reply, new_state = run_turn(state, message)

    # Add assistant message
    chat_history.append({"role": "assistant", "content": assistant_reply})

    # Trace + plan
    trace_text = extract_trace(new_state)
    plan_text = extract_plan(new_state)

    return "", chat_history, new_state, trace_text, plan_text


# ---------------------------------------------------------
# Build Gradio UI
# ---------------------------------------------------------
with gr.Blocks(title="Multi-Agent Chat") as demo:

    gr.Markdown("# 🤖 Multi‑Agent Conversational System\nRouter + Personas + Planner/Worker/Reviewer + Memory + Weather API Tools")

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                height=500,
                avatar_images=[
                    "multi_agent_chatbot/assets/user.jpg",       # user avatar
                    "multi_agent_chatbot/assets/assistant.jpg"   # assistant avatar
                ],
                buttons=['share', 'copy', 'copy_all'],
            )

            user_input = gr.Textbox(
                placeholder="Ask something...",
                label="Your message"
            )
            send_btn = gr.Button("Send")

        with gr.Column(scale=1):
            with gr.Accordion("Agent Trace", open=False):
                trace_box = gr.Markdown("No trace yet.")
            with gr.Accordion("Plan Visualization", open=False):
                plan_view = gr.Markdown("No plan yet.")

    state = gr.State(init_state())

    # Wire events
    send_btn.click(
        on_user_submit,
        inputs=[user_input, chatbot, state],
        outputs=[user_input, chatbot, state, trace_box, plan_view],
    )

    user_input.submit(
        on_user_submit,
        inputs=[user_input, chatbot, state],
        outputs=[user_input, chatbot, state, trace_box, plan_view],
    )


# ---------------------------------------------------------
# Launch app
# ---------------------------------------------------------
if __name__ == "__main__":
    _logs.info("Starting Chatbot App...")
    demo.launch()



