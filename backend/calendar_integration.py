# backend/calendar_integration.py
"""
Calendar integration for automatic interview detection and meeting context.
Supports Google Calendar, Outlook, and other calendar systems.
"""

from __future__ import annotations
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass
import re

log = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Represents a calendar event with meeting context"""
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    location: str
    meeting_url: Optional[str] = None
    is_interview: bool = False
    interview_type: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    interviewer: Optional[str] = None

class CalendarIntegration:
    """Integrates with calendar systems to detect interviews and meetings"""
    
    def __init__(self):
        self.google_credentials = self._load_google_credentials()
        self.outlook_credentials = self._load_outlook_credentials()
        self.interview_patterns = self._load_interview_patterns()
        
    def _load_google_credentials(self) -> Dict[str, str]:
        """Load Google Calendar API credentials"""
        return {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN", ""),
            "access_token": os.getenv("GOOGLE_ACCESS_TOKEN", "")
        }
    
    def _load_outlook_credentials(self) -> Dict[str, str]:
        """Load Microsoft Outlook API credentials"""
        return {
            "client_id": os.getenv("OUTLOOK_CLIENT_ID", ""),
            "client_secret": os.getenv("OUTLOOK_CLIENT_SECRET", ""),
            "tenant_id": os.getenv("OUTLOOK_TENANT_ID", ""),
            "access_token": os.getenv("OUTLOOK_ACCESS_TOKEN", "")
        }
    
    def _load_interview_patterns(self) -> Dict[str, List[str]]:
        """Load patterns for detecting interview-related events"""
        return {
            "interview_keywords": [
                "interview", "technical interview", "coding interview",
                "system design", "behavioral interview", "phone screen",
                "final round", "onsite", "virtual interview", "screening call"
            ],
            "company_indicators": [
                "hiring", "recruitment", "candidate", "position", "role",
                "job", "opportunity", "team meeting", "hiring manager"
            ],
            "technical_indicators": [
                "coding", "technical", "system design", "algorithm",
                "data structures", "leetcode", "whiteboard", "live coding"
            ],
            "meeting_platforms": [
                "zoom.us", "teams.microsoft.com", "meet.google.com",
                "webex.com", "gotomeeting.com", "bluejeans.com"
            ]
        }
    
    def analyze_event_for_interview(self, event: CalendarEvent) -> Tuple[bool, Dict[str, Any]]:
        """Analyze if an event is an interview and extract details"""
        analysis = {
            "is_interview": False,
            "confidence": 0.0,
            "interview_type": None,
            "company": None,
            "role": None,
            "interviewer": None,
            "technical_level": None,
            "preparation_suggestions": []
        }
        
        # Combine title and description for analysis
        content = f"{event.title} {event.description}".lower()
        
        # Check for interview keywords
        interview_score = 0
        for keyword in self.interview_patterns["interview_keywords"]:
            if keyword.lower() in content:
                interview_score += 10
                if keyword == "technical interview":
                    analysis["interview_type"] = "technical"
                elif keyword == "behavioral interview":
                    analysis["interview_type"] = "behavioral"
                elif keyword == "system design":
                    analysis["interview_type"] = "system_design"
        
        # Check for company indicators
        for indicator in self.interview_patterns["company_indicators"]:
            if indicator.lower() in content:
                interview_score += 5
        
        # Check for technical indicators
        technical_score = 0
        for indicator in self.interview_patterns["technical_indicators"]:
            if indicator.lower() in content:
                technical_score += 5
                interview_score += 3
        
        # Extract company name (simple heuristic)
        analysis["company"] = self._extract_company_name(event)
        
        # Extract role/position
        analysis["role"] = self._extract_role_info(event)
        
        # Extract interviewer info
        analysis["interviewer"] = self._extract_interviewer_info(event)
        
        # Determine if it's an interview
        analysis["confidence"] = min(interview_score / 50.0, 1.0)
        analysis["is_interview"] = interview_score >= 15
        
        # Set technical level based on content analysis
        if technical_score > 15:
            analysis["technical_level"] = "senior"
        elif technical_score > 5:
            analysis["technical_level"] = "mid"
        else:
            analysis["technical_level"] = "entry"
        
        # Generate preparation suggestions
        analysis["preparation_suggestions"] = self._generate_prep_suggestions(analysis, event)
        
        return analysis["is_interview"], analysis
    
    def _extract_company_name(self, event: CalendarEvent) -> Optional[str]:
        """Extract company name from event details"""
        content = f"{event.title} {event.description}"
        
        # Common patterns for company names in interview invitations
        patterns = [
            r"interview.*?(?:at|with|for)\s+([A-Z][a-zA-Z\s&]+?)(?:\s|$|,)",
            r"([A-Z][a-zA-Z\s&]+?)\s+(?:interview|hiring|recruitment)",
            r"position.*?(?:at|with)\s+([A-Z][a-zA-Z\s&]+?)(?:\s|$|,)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                # Filter out common false positives
                if len(company) > 2 and company.lower() not in ["team", "the", "your", "our"]:
                    return company
        
        return None
    
    def _extract_role_info(self, event: CalendarEvent) -> Optional[str]:
        """Extract role/position information"""
        content = f"{event.title} {event.description}".lower()
        
        # Common role patterns
        role_patterns = [
            r"(?:for|as)\s+([a-z\s]+?engineer)",
            r"(?:for|as)\s+([a-z\s]+?developer)", 
            r"(?:position|role).*?([a-z\s]+?engineer)",
            r"software\s+([a-z\s]+?)(?:\s|$)",
            r"senior\s+([a-z\s]+?)(?:\s|$)",
            r"staff\s+([a-z\s]+?)(?:\s|$)"
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_interviewer_info(self, event: CalendarEvent) -> Optional[str]:
        """Extract interviewer information from attendees or description"""
        # Check attendees for likely interviewer
        if len(event.attendees) > 0:
            # Usually the person who's not you is the interviewer
            for attendee in event.attendees:
                # Simple heuristic - if it looks like a corporate email
                if any(domain in attendee for domain in [".com", ".org", ".io"]):
                    return attendee
        
        # Check description for interviewer mentions
        content = event.description.lower()
        patterns = [
            r"interviewer:\s*([a-zA-Z\s]+)",
            r"you.?ll\s+be\s+speaking\s+with\s+([a-zA-Z\s]+)",
            r"meeting\s+with\s+([a-zA-Z\s]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _generate_prep_suggestions(self, analysis: Dict[str, Any], event: CalendarEvent) -> List[str]:
        """Generate interview preparation suggestions"""
        suggestions = []
        
        if analysis["interview_type"] == "technical":
            suggestions.extend([
                "🧠 Review data structures and algorithms",
                "💻 Practice coding problems on LeetCode/HackerRank",
                "📚 Prepare to explain your past projects in detail",
                "🏗️ Study system design if it's a senior role"
            ])
        
        elif analysis["interview_type"] == "behavioral":
            suggestions.extend([
                "📖 Prepare STAR method examples",
                "🎯 Research the company's values and culture",
                "💪 Think of challenging situations you've overcome",
                "🤝 Prepare questions about the team and role"
            ])
        
        elif analysis["interview_type"] == "system_design":
            suggestions.extend([
                "🏗️ Review system design fundamentals",
                "📈 Study scalability patterns and trade-offs",
                "🔧 Practice designing common systems (chat, feed, etc.)",
                "📊 Understand database choices and caching strategies"
            ])
        
        if analysis["company"]:
            suggestions.append(f"🏢 Research {analysis['company']}'s products and engineering culture")
        
        if analysis["technical_level"] == "senior":
            suggestions.extend([
                "👥 Prepare leadership and mentoring examples",
                "🎯 Think about technical decision-making scenarios"
            ])
        
        # Time-based suggestions
        time_to_interview = event.start_time - datetime.now()
        if time_to_interview.days <= 1:
            suggestions.append("⏰ Last-minute prep: Review your resume and recent projects")
        elif time_to_interview.days <= 7:
            suggestions.append("📅 Schedule practice interviews with peers")
        
        return suggestions
    
    def get_upcoming_events(self, days_ahead: int = 7) -> List[CalendarEvent]:
        """Get upcoming calendar events for analysis"""
        events = []
        
        # Try Google Calendar first
        if self.google_credentials.get("access_token"):
            google_events = self._fetch_google_events(days_ahead)
            events.extend(google_events)
        
        # Try Outlook Calendar
        if self.outlook_credentials.get("access_token"):
            outlook_events = self._fetch_outlook_events(days_ahead)
            events.extend(outlook_events)
        
        return events
    
    def _fetch_google_events(self, days_ahead: int) -> List[CalendarEvent]:
        """Fetch events from Google Calendar"""
        if not self.google_credentials.get("access_token"):
            log.warning("Google Calendar access token not available")
            return []
        
        headers = {
            "Authorization": f"Bearer {self.google_credentials['access_token']}",
            "Accept": "application/json"
        }
        
        # Calculate time range
        time_min = datetime.now().isoformat() + "Z"
        time_max = (datetime.now() + timedelta(days=days_ahead)).isoformat() + "Z"
        
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": True,
            "orderBy": "startTime"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            events_data = response.json()
            events = []
            
            for item in events_data.get("items", []):
                event = self._parse_google_event(item)
                if event:
                    events.append(event)
            
            return events
            
        except requests.RequestException as e:
            log.error(f"Failed to fetch Google Calendar events: {e}")
            return []
    
    def _fetch_outlook_events(self, days_ahead: int) -> List[CalendarEvent]:
        """Fetch events from Outlook Calendar"""
        if not self.outlook_credentials.get("access_token"):
            log.warning("Outlook Calendar access token not available")
            return []
        
        headers = {
            "Authorization": f"Bearer {self.outlook_credentials['access_token']}",
            "Accept": "application/json"
        }
        
        # Calculate time range
        start_time = datetime.now().isoformat()
        end_time = (datetime.now() + timedelta(days=days_ahead)).isoformat()
        
        url = "https://graph.microsoft.com/v1.0/me/events"
        params = {
            "startDateTime": start_time,
            "endDateTime": end_time,
            "$orderby": "start/dateTime"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            events_data = response.json()
            events = []
            
            for item in events_data.get("value", []):
                event = self._parse_outlook_event(item)
                if event:
                    events.append(event)
            
            return events
            
        except requests.RequestException as e:
            log.error(f"Failed to fetch Outlook Calendar events: {e}")
            return []
    
    def _parse_google_event(self, item: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Parse Google Calendar event data"""
        try:
            start_time = datetime.fromisoformat(item["start"].get("dateTime", "").replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(item["end"].get("dateTime", "").replace("Z", "+00:00"))
            
            attendees = []
            if "attendees" in item:
                attendees = [attendee.get("email", "") for attendee in item["attendees"]]
            
            meeting_url = None
            description = item.get("description", "")
            
            # Extract meeting URL from description
            url_patterns = self.interview_patterns["meeting_platforms"]
            for pattern in url_patterns:
                if pattern in description:
                    # Extract the full URL
                    import re
                    url_match = re.search(r"https?://[^\s]+", description)
                    if url_match:
                        meeting_url = url_match.group(0)
                    break
            
            return CalendarEvent(
                id=item["id"],
                title=item.get("summary", ""),
                description=description,
                start_time=start_time,
                end_time=end_time,
                attendees=attendees,
                location=item.get("location", ""),
                meeting_url=meeting_url
            )
            
        except (KeyError, ValueError) as e:
            log.warning(f"Failed to parse Google Calendar event: {e}")
            return None
    
    def _parse_outlook_event(self, item: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Parse Outlook Calendar event data"""
        try:
            start_time = datetime.fromisoformat(item["start"]["dateTime"])
            end_time = datetime.fromisoformat(item["end"]["dateTime"])
            
            attendees = []
            if "attendees" in item:
                attendees = [attendee["emailAddress"]["address"] for attendee in item["attendees"]]
            
            meeting_url = None
            if "onlineMeeting" in item and item["onlineMeeting"]:
                meeting_url = item["onlineMeeting"].get("joinUrl", "")
            
            return CalendarEvent(
                id=item["id"],
                title=item.get("subject", ""),
                description=item.get("body", {}).get("content", ""),
                start_time=start_time,
                end_time=end_time,
                attendees=attendees,
                location=item.get("location", {}).get("displayName", ""),
                meeting_url=meeting_url
            )
            
        except (KeyError, ValueError) as e:
            log.warning(f"Failed to parse Outlook Calendar event: {e}")
            return None
    
    def monitor_upcoming_interviews(self) -> List[Dict[str, Any]]:
        """Monitor and analyze upcoming interviews"""
        events = self.get_upcoming_events(days_ahead=14)
        interviews = []
        
        for event in events:
            is_interview, analysis = self.analyze_event_for_interview(event)
            
            if is_interview:
                interview_data = {
                    "event": event,
                    "analysis": analysis,
                    "time_until": event.start_time - datetime.now(),
                    "preparation_needed": analysis["confidence"] > 0.7
                }
                interviews.append(interview_data)
        
        # Sort by time until interview
        interviews.sort(key=lambda x: x["time_until"])
        
        return interviews
    
    def setup_interview_notifications(self) -> Dict[str, Any]:
        """Setup automatic notifications for detected interviews"""
        interviews = self.monitor_upcoming_interviews()
        notifications = []
        
        for interview in interviews:
            time_until = interview["time_until"]
            
            # Schedule notifications at different intervals
            if timedelta(hours=23) < time_until < timedelta(hours=25):
                # 24 hours before
                notifications.append({
                    "type": "preparation_reminder",
                    "message": f"Interview tomorrow at {interview['event'].title}",
                    "suggestions": interview["analysis"]["preparation_suggestions"]
                })
            
            elif timedelta(hours=1) < time_until < timedelta(hours=3):
                # 2 hours before
                notifications.append({
                    "type": "final_prep",
                    "message": f"Interview in 2 hours: {interview['event'].title}",
                    "suggestions": ["🧘 Relax and review key points", "💻 Test your setup and camera"]
                })
            
            elif timedelta(minutes=15) < time_until < timedelta(minutes=30):
                # 15-30 minutes before - activate stealth mode
                notifications.append({
                    "type": "activate_stealth",
                    "message": f"Interview starting soon - activating AI assistant stealth mode",
                    "action": "enable_interview_mode"
                })
        
        return {
            "scheduled_notifications": notifications,
            "total_interviews": len(interviews),
            "next_interview": interviews[0] if interviews else None
        }

# Integration with main system
def auto_detect_interview_mode():
    """Auto-detect and activate interview mode based on calendar"""
    calendar = CalendarIntegration()
    interviews = calendar.monitor_upcoming_interviews()
    
    for interview in interviews:
        time_until = interview["time_until"]
        
        # If interview is starting in next 30 minutes, activate interview mode
        if timedelta(minutes=0) <= time_until <= timedelta(minutes=30):
            return {
                "activate_interview_mode": True,
                "interview_details": interview["analysis"],
                "company": interview["analysis"]["company"],
                "interview_type": interview["analysis"]["interview_type"],
                "preparation_suggestions": interview["analysis"]["preparation_suggestions"]
            }
    
    return {"activate_interview_mode": False}

if __name__ == "__main__":
    # Test calendar integration
    calendar = CalendarIntegration()
    interviews = calendar.monitor_upcoming_interviews()
    
    print(f"Found {len(interviews)} upcoming interviews:")
    for interview in interviews:
        print(f"- {interview['event'].title} at {interview['event'].start_time}")
        print(f"  Company: {interview['analysis']['company']}")
        print(f"  Type: {interview['analysis']['interview_type']}")
        print(f"  Confidence: {interview['analysis']['confidence']:.2f}")
        print()
