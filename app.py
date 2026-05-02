import os
import json
import textwrap
import subprocess
import shutil
import requests
from typing import Optional, List, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from gtts import gTTS
from mutagen.mp3 import MP3

app = FastAPI(title="Teaching Monster AI Agent")

OUTPUT_DIR = "static_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=OUTPUT_DIR), name="static")

class GenerationRequest(BaseModel):
    request_id: str
    course_requirement: str
    student_persona: str

class GenerationResponse(BaseModel):
    video_url: str
    subtitle_url: Optional[str] = None
    supplementary_url: Optional[Union[List[str], str]] = None

def generate_teaching_script(course: str, persona: str) -> list:
    """捨棄 SDK，直接使用 REST API 呼叫 Gemini"""
    api_key = os.getenv("GEMINI_API_KEY")
    
    fallback_script = [
        {
            "title": "System Notice",
            "blocks": [
                {"text": "The system is currently unable to generate dynamic content."},
                {"text": "Please check your API key configuration or try again later."}
            ]
        }
    ]

    if not api_key:
        print("Warning: GEMINI_API_KEY is not set.")
        return fallback_script

    try:
        prompt = f"""
        You are an AI teaching assistant.
        Create a short, engaging video script explaining the following topic: "{course}".
        Tailor the explanation for this specific student persona: "{persona}".
        
        You MUST respond STRICTLY in the following JSON array format:
        [
            {{
                "title": "Main Title for Scene 1",
                "blocks": [
                    {{"text": "First sentence of the explanation."}},
                    {{"text": "Second sentence of the explanation."}}
                ]
            }}
        ]
        Limit the entire script to a maximum of 2 scenes, with 3 short sentences per scene to keep the rendering time low.
        """

        # 已替換為 gemini-1.5-flash-latest，解決 404 與 limit: 0 的問題
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.7
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response_data = response.json()

        if "error" in response_data:
            print(f"Gemini API Error: {response_data['error']}")
            return fallback_script

        # 解析回傳的 JSON 結構
        result_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
        script_data = json.loads(result_text)
        return script_data

    except Exception as e:
        print(f"API Request Failed: {str(e)}")
        return fallback_script

# 通用型 Manim 動畫模板
MANIM_TEMPLATE = r"""
from manim import *
import json
import textwrap

class TeachingScene(Scene):
    def construct(self):
        with open("static_output/current_script.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        sub_bg = Rectangle(width=config.frame_width, height=1.5).set_fill(BLACK, opacity=0.95).set_stroke(width=0).to_edge(DOWN, buff=0)
        self.add(sub_bg)
        subtitle = Text(" ", font_size=24).move_to(sub_bg.get_center())
        self.add(subtitle)

        def play_block(block):
            self.add_sound(block["audio_path"])
            
            wrapped_sub = textwrap.fill(block["text"], width=65)
            subtitle.become(Text(wrapped_sub, font_size=24, line_spacing=1).move_to(sub_bg.get_center()))
            
            wrapped_main = textwrap.fill(block["text"], width=40)
            main_text = Text(wrapped_main, font_size=36, line_spacing=1.2).move_to(UP * 0.5)
            
            duration = block["duration"]
            
            self.play(FadeIn(main_text), run_time=min(0.5, duration/2))
            remaining_time = duration - min(0.5, duration/2)
            if remaining_time > 0:
                self.wait(remaining_time)
            
            self.play(FadeOut(main_text), run_time=0.2)

        for scene in data:
            title_text = scene.get("title", "Topic")
            title = Text(title_text, color=BLUE, font_size=40).to_edge(UP, buff=0.5)
            self.play(Write(title), run_time=1.0)
            
            blocks = scene.get("blocks", [])
            for block in blocks:
                play_block(block)
                
            self.play(FadeOut(title))

        self.wait(1)
"""

def build_video_pipeline(request_id: str, course: str, persona: str) -> str:
    script_data = generate_teaching_script(course, persona)
    
    for scene_idx, scene in enumerate(script_data):
        for block_idx, block in enumerate(scene.get("blocks", [])):
            audio_path = os.path.join(OUTPUT_DIR, f"audio_{request_id}_{scene_idx}_{block_idx}.mp3")
            tts = gTTS(text=block["text"], lang='en', tld='us')
            tts.save(audio_path)
            
            audio_info = MP3(audio_path)
            block["audio_path"] = audio_path
            block["duration"] = audio_info.info.length

    json_path = os.path.join(OUTPUT_DIR, "current_script.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f)

    manim_script_path = "manim_generator.py"
    with open(manim_script_path, "w", encoding="utf-8") as f:
        f.write(MANIM_TEMPLATE)

    cmd = [
        "manim", "-ql", manim_script_path, "TeachingScene",
        "--media_dir", OUTPUT_DIR
    ]
    subprocess.run(cmd, check=True)

    generated_video = os.path.join(OUTPUT_DIR, "videos", "manim_generator", "480p15", "TeachingScene.mp4")
    output_filename = f"{request_id}.mp4"
    final_dest = os.path.join(OUTPUT_DIR, output_filename)
    
    if os.path.exists(generated_video):
        shutil.move(generated_video, final_dest)
        
    return output_filename

@app.post("/generate", response_model=GenerationResponse)
async def api_generate(req: GenerationRequest, request: Request):
    try:
        video_filename = build_video_pipeline(req.request_id, req.course_requirement, req.student_persona)
        base_url = str(request.base_url).rstrip("/")
        video_url = f"{base_url}/static/{video_filename}"
        return GenerationResponse(video_url=video_url, subtitle_url=None, supplementary_url=[])
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Video generation failed.")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860)