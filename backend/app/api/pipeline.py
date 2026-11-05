from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
from datetime import datetime
from pathlib import Path

from app.services.video.demo_renderer import generate_script_groq, generate_voiceover_edge, render_video_demo

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

class ScriptRequest(BaseModel):
    product_name: str
    price: int
    category: str = "Nhà cửa"

class TTSRequest(BaseModel):
    text: str
    job_id: str

class RenderRequest(BaseModel):
    job_id: str
    product_name: str
    price: int
    script: dict

class PipelineRequest(BaseModel):
    product_name: str
    price: int
    category: str = "Nhà cửa"

@router.post("/script")
def api_generate_script(req: ScriptRequest):
    try:
        script = generate_script_groq(req.product_name, req.price, req.category)
        return {"status": "success", "script": script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tts")
async def api_generate_tts(req: TTSRequest):
    out_dir = Path("storage/demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(out_dir / f"voiceover_{req.job_id}.mp3")
    
    try:
        await generate_voiceover_edge(req.text, audio_path)
        return {"status": "success", "audio_path": audio_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/render")
def api_render_video(req: RenderRequest):
    out_dir = Path("storage/demo")
    audio_path = str(out_dir / f"voiceover_{req.job_id}.mp3")
    video_path = str(out_dir / f"video_{req.job_id}.mp4")
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=400, detail="Voiceover not found for job_id")
        
    try:
        render_video_demo(audio_path, req.script, req.product_name, req.price, video_path)
        return {"status": "success", "video_path": video_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run_all")
async def api_run_pipeline(req: PipelineRequest):
    """Run all steps of the pipeline synchronously."""
    try:
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Script
        script = generate_script_groq(req.product_name, req.price, req.category)
        
        # 2. TTS
        out_dir = Path("storage/demo")
        out_dir.mkdir(parents=True, exist_ok=True)
        audio_path = str(out_dir / f"voiceover_{job_id}.mp3")
        await generate_voiceover_edge(script["full_script"], audio_path)
        
        # 3. Render
        video_path = str(out_dir / f"video_{job_id}.mp4")
        render_video_demo(audio_path, script, req.product_name, req.price, video_path)
        
        # 4. Mock Publish
        publish_result = {
            "status": "simulated",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "message": "TikTok API approval pending. Video ready for manual upload."
        }
        
        return {
            "status": "success",
            "job_id": job_id,
            "script": script,
            "audio_path": audio_path,
            "video_path": video_path,
            "publish_result": publish_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
