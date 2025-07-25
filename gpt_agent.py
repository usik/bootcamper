# gpt_agent.py
import openai
import json
import os

PROMPT_DIR = "prompts"

STYLE_MAP = {
    "조교": "drill_sergeant.txt",
    "친구": "friend.txt",
    "연인": "lover.txt",
    "세계 최고의 트레이너": "elite_trainer.txt"
}

def load_prompt(style: str) -> str:
    filename = STYLE_MAP.get(style, "elite_trainer.txt")
    path = os.path.join(PROMPT_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def get_gpt_response(prompt_input: str, style: str):
    system_prompt = load_prompt(style)
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_input}
        ],
        temperature=0.8
    )

    full_response = response.choices[0].message.content.strip()

    # 구조화된 응답을 위한 기본 패턴 가정
    # GPT는 아래 포맷을 지켜야 함
    # 루틴 JSON: {...}
    # 피드백: ...

    if "루틴 JSON:" in full_response:
        parts = full_response.split("루틴 JSON:")
        gpt_text = parts[0].strip()
        routine_json_raw = parts[1].split("피드백:")[0].strip()
        feedback = full_response.split("피드백:")[-1].strip()

        try:
            routine_json = json.loads(routine_json_raw)
        except json.JSONDecodeError:
            routine_json = {"error": "JSON 파싱 실패", "raw": routine_json_raw}
    else:
        gpt_text = full_response
        routine_json = {}
        feedback = "응답에서 루틴 정보를 찾을 수 없습니다."

    return gpt_text, routine_json, feedback
