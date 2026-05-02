import os
import json
import textwrap
import subprocess
import shutil
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
    return [
        {
            "type": "problem",
            "title": "1. The Problem",
            "blocks": [
                {"text": "Have you ever wondered why we need calculus?"},
                {"text": f"Imagine driving a car. Your distance traveled over time is given by the formula: d of t equals 5 t squared."},
                {"text": "Finding your average speed over a long trip is easy."},
                {"text": "But what if we want to know your exact speed at the exact moment the clock hits 2 seconds?"},
                {"text": "To solve this problem, we must understand a new mathematical concept."}
            ]
        },
        {
            "type": "concept",
            "title": "2. The Concept",
            "blocks": [
                {"text": "Let us look at the mathematics of motion."},
                {"text": "On a graph, the distance over time can be represented as a curve."},
                {"text": "The average speed is the slope of a line connecting two different points. This is called a secant line."},
                {"text": "But an exact moment is just one single point on the curve. Watch as we shrink the time gap to zero."},
                {"text": "The secant line becomes a tangent line. This process is called taking the limit, giving us the exact derivative."}
            ]
        },
        {
            "type": "solution",
            "title": "3. The Solution",
            "blocks": [
                {"text": "Now, let us bring this concept back to our driving problem."},
                {"text": "First, using basic algebra, we calculate the average speed between 2 and 2.1 seconds."},
                {"text": "The result is 20.5 meters per second. This is the slope of our secant line."},
                {"text": "Next, we use calculus to find the exact speed. The derivative of 5 t squared is 10 t."},
                {"text": "By plugging in exactly 2 seconds, we get exactly 20 meters per second."},
                {"text": "Notice how the average speed of 20.5 was just an approximation of our exact speed of 20."}
            ]
        },
        {
            "type": "mindmap",
            "title": "4. Summary Mind Map",
            "blocks": [
                {"text": "Let us summarize our learning with a mind map."},
                {"text": "Our main goal is to find the Rate of Change."},
                {"text": "The traditional way uses Algebra to find the Average Rate between two points."},
                {"text": "The advanced way uses Calculus and Limits to find the Instantaneous Rate at one exact point."},
                {"text": "By understanding both, you have successfully solved the driving problem."}
            ]
        }
    ]

MANIM_TEMPLATE = r"""
from manim import *
import json
import textwrap

class TeachingScene(Scene):
    def construct(self):
        with open("static_output/current_script.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # 固定的底部字幕區塊
        sub_bg = Rectangle(width=config.frame_width, height=1.5).set_fill(BLACK, opacity=0.95).set_stroke(width=0).to_edge(DOWN, buff=0)
        self.add(sub_bg)
        subtitle = Text(" ", font_size=24).move_to(sub_bg.get_center())
        self.add(subtitle)

        visual_center = UP * 0.5
        
        # 負責將動畫與語音精確對齊的控制函數
        def play_block(block, anims=None, anim_time=None):
            self.add_sound(block["audio_path"])
            wrapped_text = textwrap.fill(block["text"], width=65)
            subtitle.become(Text(wrapped_text, font_size=24, line_spacing=1).move_to(sub_bg.get_center()))
            
            duration = block["duration"]
            if anims:
                atime = min(1.0, duration - 0.1) if anim_time is None else min(anim_time, duration - 0.1)
                if atime > 0:
                    self.play(*anims, run_time=atime)
                rem = duration - atime
                if rem > 0:
                    self.wait(rem + 0.1)
                else:
                    self.wait(0.1)
            else:
                self.wait(duration + 0.1)

        for scene in data:
            title = Text(scene["title"], color=BLUE, font_size=36).to_edge(UP, buff=0.3)
            self.play(Write(title), run_time=1.0)
            blocks = scene["blocks"]
            stype = scene["type"]

            if stype == "problem":
                play_block(blocks[0])
                
                eq_d = MathTex("d(t) = 5t^2", font_size=48).move_to(visual_center + UP*0.5)
                play_block(blocks[1], [Write(eq_d)])
                
                play_block(blocks[2])
                
                question = MathTex(r"v(2) = \, ?", color=YELLOW, font_size=48).next_to(eq_d, DOWN, buff=1.0)
                play_block(blocks[3], [FadeIn(question)])
                
                play_block(blocks[4])
                
            elif stype == "concept":
                play_block(blocks[0])
                
                axes = Axes(x_range=[0, 3], y_range=[0, 9], x_length=4, y_length=4).move_to(visual_center + LEFT * 3.5)
                curve = axes.plot(lambda x: x**2, color=WHITE)
                
                t_val = ValueTracker(2.8)
                dot_fixed = Dot(axes.c2p(1, 1), color=YELLOW).scale(1.2)
                dot_move = always_redraw(lambda: Dot(axes.c2p(t_val.get_value(), t_val.get_value()**2), color=RED).scale(1.2))
                
                def get_secant():
                    x1 = 1.0
                    x2 = t_val.get_value()
                    if abs(x2 - x1) < 0.001: x2 = x1 + 0.001
                    y1, y2 = 1.0, x2**2
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    p1 = axes.c2p(0, b)
                    p2 = axes.c2p(3, m * 3 + b)
                    return Line(p1, p2, color=GREEN)
                
                secant = always_redraw(get_secant)
                
                play_block(blocks[1], [Create(axes), Create(curve)])
                play_block(blocks[2], [FadeIn(dot_fixed), FadeIn(dot_move), Create(secant)])
                self.add(dot_fixed, dot_move, secant)
                
                play_block(blocks[3], [t_val.animate.set_value(1.001)], anim_time=3.0)
                
                limit_eq = MathTex(r"f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}", font_size=40).move_to(visual_center + RIGHT * 2.5)
                play_block(blocks[4], [Write(limit_eq)])

            elif stype == "solution":
                play_block(blocks[0])
                
                # 左半部：代數方法隔離
                avg_group = VGroup(
                    Text("Algebra", font_size=24, color=GREEN),
                    MathTex(r"v_{avg} = \frac{d(2.1)-d(2)}{2.1-2}", font_size=36),
                    MathTex(r"= 20.5 \text{ m/s}", font_size=36, color=GREEN)
                ).arrange(DOWN).move_to(visual_center + LEFT * 3.5)
                
                play_block(blocks[1], [FadeIn(avg_group[0]), Write(avg_group[1])])
                play_block(blocks[2], [Write(avg_group[2])])
                
                # 右半部：微積分方法隔離
                calc_group = VGroup(
                    Text("Calculus", font_size=24, color=RED),
                    MathTex(r"d'(t) = 10t", font_size=36),
                    MathTex(r"d'(2) = 20 \text{ m/s}", font_size=36, color=YELLOW)
                ).arrange(DOWN).move_to(visual_center + RIGHT * 3.5)
                
                play_block(blocks[3], [FadeIn(calc_group[0]), Write(calc_group[1])])
                play_block(blocks[4], [Write(calc_group[2])])
                
                box = SurroundingRectangle(calc_group[2], color=YELLOW)
                play_block(blocks[5], [Create(box)])

            elif stype == "mindmap":
                play_block(blocks[0])
                
                center_node = Text("Rate of Change", font_size=32).move_to(visual_center + UP * 1.5)
                c_box = SurroundingRectangle(center_node, color=BLUE)
                play_block(blocks[1], [FadeIn(center_node), Create(c_box)])
                
                left_node = VGroup(
                    Text("Average Rate", font_size=24),
                    Text("(Algebra / 2 Points)", font_size=20, color=GREEN)
                ).arrange(DOWN).move_to(visual_center + LEFT * 3.5 + DOWN * 0.5)
                l_box = SurroundingRectangle(left_node, color=GREEN)
                l_line = Line(c_box.get_bottom(), l_box.get_top(), color=GRAY)
                play_block(blocks[2], [Create(l_line), FadeIn(left_node), Create(l_box)])
                
                right_node = VGroup(
                    Text("Instantaneous Rate", font_size=24),
                    Text("(Calculus / 1 Point)", font_size=20, color=RED)
                ).arrange(DOWN).move_to(visual_center + RIGHT * 3.5 + DOWN * 0.5)
                r_box = SurroundingRectangle(right_node, color=RED)
                r_line = Line(c_box.get_bottom(), r_box.get_top(), color=GRAY)
                play_block(blocks[3], [Create(r_line), FadeIn(right_node), Create(r_box)])
                
                play_block(blocks[4])

            self.clear()
            self.add(sub_bg, subtitle)
"""

def build_video_pipeline(request_id: str, course: str, persona: str) -> str:
    script_data = generate_teaching_script(course, persona)
    
    for scene_idx, scene in enumerate(script_data):
        for block_idx, block in enumerate(scene["blocks"]):
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