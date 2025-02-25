from google import genai
from google.genai import types
import time
import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize Google API client
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)
model_name = "gemini-2.0-flash-exp"


USER_PROMPT = """Analyze the video and identify any household issues such as broken/leaking faucets, cracked doors, damp walls etc. Generate a structured technical report using the following format:

ISSUE TYPE:
[Single line description of the primary issue]

LOCATION:
[Specific location details]

DETAILED ASSESSMENT:
[Thorough description of the damage/issue]

PHYSICAL CHARACTERISTICS:
- [Bullet points describing measurable/observable features]
- [Include dimensions, patterns, extent of damage where visible]

TECHNICAL IMPLICATIONS:
- [List of structural/functional impacts]
- [Safety concerns]
- [Security implications]
- [Environmental effects]

REPAIR REQUIREMENTS:
1. [Prioritized list of necessary repairs]
2. [Include safety measures required]
3. [Special considerations for repair work]

DOCUMENTATION NOTES:
- [Additional relevant observations]
- [Areas needing further inspection]
"""

system_instruction = (
    """You are a professional property inspection assistant specializing in technical documentation. Your role is to analyze video content showing household issues and produce structured technical reports. Follow these key principles:

1. DOCUMENTATION STYLE:
- Maintain strictly professional and technical language
- Never use conversational phrases or first-person language
- Exclude greetings, introductions, and concluding remarks
- Avoid hedging words like "seems," "appears," or "might"

2. REPORT STRUCTURE:
- Use consistent hierarchical formatting
- Present information in clearly defined sections
- Employ bullet points for discrete observations
- Use numbered lists only for sequential procedures

3. TECHNICAL DETAILS:
- Prioritize measurable and observable characteristics
- Include specific measurements when visible
- Document patterns and extent of damage precisely
- Note spatial relationships and orientations

4. SAFETY AND COMPLIANCE:
- Always highlight immediate safety concerns
- Include relevant safety procedures for repairs
- Note potential code violations or compliance issues
- Document security implications

5. COMMUNICATION STANDARDS:
- Use industry-standard terminology
- Maintain objective, fact-based descriptions
- Exclude subjective assessments
- Omit speculative content

6. FOCUS AREAS:
- Structural elements
- Mechanical systems
- Electrical components
- Plumbing systems
- Environmental conditions
- Safety hazards
- Security vulnerabilities

FORMAT ALL OBSERVATIONS USING THE PRESCRIBED TEMPLATE STRUCTURE IN THE USER PROMPT.""",
)


@app.route("/")
def index():
    return render_template("index.html")


def upload_video_gcp(video_file_name):
    video_file = client.files.upload(file=video_file_name)

    while video_file.state == "PROCESSING":
        print("Waiting for video to be processed.")
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state == "FAILED":
        raise ValueError(video_file.state)
    print(f"Video processing complete: " + video_file.uri)

    return video_file


@app.route("/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file"}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded video
    video_path = os.path.join("uploads", "recorded_video.webm")
    os.makedirs("uploads", exist_ok=True)
    video_file.save(video_path)

    try:
        # Upload to Google AI
        video_file = upload_video_gcp(video_path)

        # Process the video
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=video_file.uri, mime_type=video_file.mime_type
                        )
                    ],
                ),
                USER_PROMPT,
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
            ),
        )

        return jsonify({"success": True, "analysis": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Enable HTTPS support for development environment
    # For production, Render handles HTTPS
    app.run(host="0.0.0.0", port=port)
