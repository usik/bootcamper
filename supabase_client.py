# supabase_client.py
import os
from supabase import create_client, Client
from datetime import datetime

class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.supabase: Client = create_client(url, key)

    def create_user(self, nickname, gender, height, weight, inbody, goal, style):
        response = self.supabase.table("users").insert({
            "nickname": nickname,
            "gender": gender,
            "height": height,
            "weight": weight,
            "inbody": inbody,
            "goal": goal,
            "style": style,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return response.data[0]

    def create_user_with_id(self, user_id, nickname, gender, height, weight, inbody, goal, style):
        response = self.supabase.table("users").insert({
            "id": user_id,
            "nickname": nickname,
            "gender": gender,
            "height": height,
            "weight": weight,
            "inbody": inbody,
            "goal": goal,
            "style": style,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return response.data[0]

    def log_session(self, user_id, date_str, condition, routine, feedback, mood=None, energy=None, sleep=None):
        response = self.supabase.table("sessions").insert({
            "user_id": user_id,
            "date": date_str,
            "condition": condition,
            "routine": routine,
            "feedback": feedback,
            "mood": mood,
            "energy": energy,
            "sleep": sleep,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return response.data

    def get_user_sessions(self, user_id):
        response = self.supabase.table("sessions").select("*") \
            .eq("user_id", user_id).order("date", desc=True).limit(10).execute()
        return response.data

    def get_user(self, user_id):
        response = self.supabase.table("users").select("*").eq("id", user_id).single().execute()
        return response.data
