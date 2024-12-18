from shiny import App, reactive, render, ui
from openai import OpenAI
import os

try:
    from setup import api_key1
except ImportError:
    pass
    
api_key1 = os.getenv("OPENAI_API_KEY")
    
app_info = """
This app uses OpenAI 4o-mini to generate messages based on user inputs.
It's inspired by [Outlook's Copilot integration](https://support.microsoft.com/en-us/office/draft-an-email-message-with-copilot-in-outlook-3eb1d053-89b8-491c-8a6e-746015238d9b).
"""

app_ui = ui.page_fluid(
    ui.h1("Draft Master: an AI-powered email/message drafting tool"),
    ui.markdown(app_info),
    ui.row([
        ui.input_password(
            "api_key", 
            "OpenAI API Key",
            value = api_key1,
        ),
        ui.input_select(
            "tone",
            "Select tone",
            choices=["Direct", "Casual", "Formal", "Make it a poem"]
        ),
        ui.input_select(
            "length",
            "Select length",
            choices=["Short", "Medium", "Long"]
        ),
    ]),
    ui.row([
        ui.input_text_area("initial_message", "Initial message or instructions", height="100px"),
        ui.input_text_area(
        "custom_instructions",
        "Custom instructions (optional)",
        placeholder="Add any specific requirements...",
        height="100px"
        ),
        ui.column(4,
            ui.row([
                ui.input_switch("email_mode", "Email mode", value = True),
                ui.input_switch("fix_spelling", "Fix spelling"),
                ui.input_switch("fix_grammar", "Fix grammar"),
                ui.input_switch("fix_punctuation", "Fix punctuation"),
            ])
        ),
    ]),
    ui.input_action_button("generate", "Generate Message", class_="btn-primary"),
    ui.input_action_button("reset", "Reset", class_="btn-secondary"),
    ui.hr(),
    ui.p("Note: Your API key is never stored and is only used for message generation."),
    ui.card(
        ui.output_ui("generated_message"),
        ui.panel_conditional(
            "input.generate",
            ui.input_action_button("copy", "Copy to Clipboard", class_="btn-primary"),
            ui.tags.script(
                """
                $(function() {
                    Shiny.addCustomMessageHandler("copy_to_clipboard", function(message) {
                        navigator.clipboard.writeText(message.text);
                    });
                });
                """
            ),
            ui.input_action_button("adjust", "Adjust"),
            ui.input_select("adjust_option", "Adjust the generated message (optional)",
                choices=[
                    "Make it longer", 
                    "Make it shorter",
                    "Make it sound more formal",
                    "Make it sound more direct",
                    "Make it sound more casual",
                    "Make it a poem"
                ],
            ),
        ),
    ),
)

def server(input, output, session):
    message = reactive.Value("")
    
    @reactive.effect
    @reactive.event(input.reset)
    def _():
        ui.update_text_area("initial_message", value="")
        ui.update_text_area("custom_instructions", value="")
        message.set("")
    
    @reactive.effect
    @reactive.event(input.generate)
    def generate_message():
        api_key = input.api_key()
        if not api_key:
            ui.notification_show("Please enter your OpenAI API key.", type="error")
            return
        client = OpenAI(api_key=api_key)
        # Construct the prompt based on user inputs
        length_map = {
            "Short": "about 50 words",
            "Medium": "about 100 words",
            "Long": "about 200 words"
        }
        special_instructions = []
        if input.fix_spelling():
            special_instructions.append("Fix spelling")
        if input.fix_grammar():
            special_instructions.append("Fix grammar")
        if input.fix_punctuation():
            special_instructions.append("Fix punctuation")
        prompt = f"""Please help me draft a message with the following specifications:
        Initial message/instructions: {input.initial_message()}
        Tone: {input.tone()}
        Length: {length_map[input.length()]}
        Additional instructions: {input.custom_instructions() if input.custom_instructions() else 'None'}
        Special instructions: {', '.join(special_instructions) if special_instructions else 'None'}
        Format mode: {"as an email" if input.email_mode() else "as a message"}
        Ensure you follow good spacing and formatting.
        Only provide the message text, no need to include the instructions or specifications.
        """ 
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that helps draft emails and text messages."},
                    {"role": "user", "content": prompt}
                ]
            )
            generate_message = response.choices[0].message.content.strip()
            ui.notification_show("Message generated successfully!", duration=3)
            message.set(generate_message)
        except Exception as e:
            ui.notification_show(f"Error: {str(e)}", type="error")
            
    @reactive.effect
    @reactive.event(input.adjust)
    def adjust_message():
        option = input.adjust_option()
        if not option:
            ui.notification_show("Please select an option to adjust the message.", type="error")
            return
        if not message():
            ui.notification_show("No message to adjust.", type="error")
            return
        api_key = input.api_key()
        if not api_key:
            ui.notification_show("Please enter your OpenAI API key.", type="error")
            return
        client = OpenAI(api_key=api_key)
        prompt = f"""Please help me adjust a message with the following specifications:
        Initial message: {message.get()}
        Please adjust the message to: {option}
        Ensure you follow good spacing and formatting.
        Only provide the message text, no need to include the instructions or specifications.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that helps draft emails and text messages."},
                    {"role": "user", "content": prompt}
                ]
            )
            adjusted_message = response.choices[0].message.content.strip()
            ui.notification_show("Message adjusted successfully!", duration=3)
            message.set(adjusted_message)
        except Exception as e:
            ui.notification_show(f"Error: {str(e)}", type="error")
    
    @output
    @render.text
    def generated_message():
        if not message():
            return "Generated message will appear here..."
        return ui.markdown(message())
    
    @reactive.effect
    @reactive.event(input.copy)
    async def _():
        if message.get() != "":
            ui.notification_show("Text copied to clipboard!", duration=3)
            await session.send_custom_message(
                "copy_to_clipboard", 
                {"text": message.get()}
            )
        else:
            ui.notification_show("No text to copy!", type="warning", duration=3)


app = App(app_ui, server)
