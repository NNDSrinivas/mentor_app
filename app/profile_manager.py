# Profile and Resume Management for AI Interview Assistant
# This module handles user profile data and resume analysis for personalized responses

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, cast

# Optional document processing imports
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    PyPDF2 = None  # type: ignore
    
try:
    import docx2txt
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    docx2txt = None  # type: ignore
    
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.profile_file = os.path.join(data_dir, "user_profile.json")
        self.resume_dir = os.path.join(data_dir, "resumes")
        
        # Create directories if they don't exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(self.resume_dir, exist_ok=True)
        
        # Initialize empty profile
        self.profile_data = self.load_profile()
        
    def load_profile(self) -> Dict[str, Any]:
        """Load existing profile or create empty one"""
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                    logger.info("✅ Loaded existing user profile")
                    return profile
            except Exception as e:
                logger.error(f"❌ Error loading profile: {e}")
        
        # Return empty profile structure
        empty_profile = {
            "personal": {
                "fullName": "",
                "currentRole": "",
                "experienceYears": "",
                "location": "",
                "currentCompany": "",
                "industry": "",
                "careerGoals": ""
            },
            "skills": {
                "selected": [],
                "additional": []
            },
            "experience": {
                "keyProjects": "",
                "achievements": "",
                "challenges": ""
            },
            "preferences": {
                "communicationStyle": "confident",
                "responseLength": "medium",
                "personalityTraits": ""
            },
            "resume": {
                "analyzed": False,
                "extractedInfo": {},
                "fullText": "",
                "lastAnalyzed": None
            },
            "lastUpdated": datetime.now().isoformat()
        }
        logger.info("📝 Created new empty profile")
        return empty_profile
    
    def save_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Save profile data to file"""
        try:
            profile_data["lastUpdated"] = datetime.now().isoformat()
            self.profile_data = profile_data
            
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            logger.info("✅ Profile saved successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving profile: {e}")
            return False
    
    def get_profile(self) -> Dict[str, Any]:
        """Get current profile data"""
        return self.profile_data
    
    def analyze_resume(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """Analyze uploaded resume and extract information"""
        try:
            # Extract text based on file type
            text = self._extract_text_from_file(file_path, original_filename)
            
            if not text:
                return {"error": "Could not extract text from resume"}
            
            # Analyze the resume text
            analysis = self._analyze_resume_text(text)
            
            # Update profile with resume data
            self.profile_data["resume"] = {
                "analyzed": True,
                "extractedInfo": analysis,
                "fullText": text[:5000],  # Store first 5000 chars
                "lastAnalyzed": datetime.now().isoformat(),
                "filename": original_filename
            }
            
            # Auto-update profile fields with extracted info
            self._auto_update_profile_from_resume(analysis)
            
            # Save updated profile
            self.save_profile(self.profile_data)
            
            logger.info("✅ Resume analyzed and profile updated")
            return {
                "success": True,
                "extracted_info": analysis,
                "auto_updated_fields": ["skills", "experience", "personal"]
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing resume: {e}")
            return {"error": str(e)}
    
    def _extract_text_from_file(self, file_path: str, filename: str) -> str:
        """Extract text from various file formats"""
        try:
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext in ['.doc', '.docx']:
                return self._extract_from_docx(file_path)
            elif file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
                
        except Exception as e:
            logger.error(f"❌ Error extracting text: {e}")
            return ""
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        if not PDF_AVAILABLE:
            logger.warning("PyPDF2 not available - cannot extract PDF text")
            return "PDF processing not available - install PyPDF2 to enable PDF resume parsing"
            
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = cast(Any, PyPDF2).PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"❌ Error extracting PDF: {e}")
            return ""
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        if not DOCX_AVAILABLE:
            logger.warning("docx2txt not available - cannot extract DOCX text")
            return "DOCX processing not available - install docx2txt to enable DOCX resume parsing"
            
        try:
            return cast(Any, docx2txt).process(file_path)
        except Exception as e:
            logger.error(f"❌ Error extracting DOCX: {e}")
            return ""
    
    def _analyze_resume_text(self, text: str) -> Dict[str, Any]:
        """Analyze resume text using AI for accurate extraction"""
        try:
            # Use AI to analyze the resume for much better accuracy
            from app.ai_assistant import AIAssistant
            ai_assistant = AIAssistant()
            
            analysis_prompt = f"""
Extract comprehensive information from this resume as JSON. Be accurate and detailed:

{text[:3000]}

Return only this JSON (no other text):
{{
"name": "Full name from resume",
"current_role": "Most recent job title", 
"current_company": "Most recent company name",
"experience_years": "0-1, 1-3, 3-5, 5-8, or 8+",
"skills": ["primary technical skills - up to 10"],
"location": "City, State",
"industry": "Primary industry sector",
"key_projects": "Brief summary of notable projects and technologies used",
"achievements": "Key accomplishments with metrics where available"
}}
            """
            
            # Get AI analysis using the same method as web interface
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            ai_context = {
                'type': 'resume_analysis',
                'timestamp': datetime.now().isoformat(),
                'source': 'profile_manager'
            }
            
            response = loop.run_until_complete(
                ai_assistant._generate_ai_response(analysis_prompt, ai_context)
            )
            loop.close()
            
            # Try to parse JSON response
            import json
            try:
                # Clean the response to extract just the JSON
                response_clean = response.strip()
                
                # Remove any markdown formatting
                if response_clean.startswith('```'):
                    lines = response_clean.split('\n')
                    json_start = -1
                    json_end = -1
                    for i, line in enumerate(lines):
                        if '{' in line and json_start == -1:
                            json_start = i
                        if '}' in line and json_start != -1:
                            json_end = i
                    if json_start != -1 and json_end != -1:
                        response_clean = '\n'.join(lines[json_start:json_end+1])
                
                # Try to find JSON in the response
                if '{' in response_clean and '}' in response_clean:
                    start = response_clean.find('{')
                    # Find the last complete closing brace
                    brace_count = 0
                    end = -1
                    for i, char in enumerate(response_clean[start:], start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    
                    if end != -1:
                        response_clean = response_clean[start:end]
                    else:
                        # If incomplete, try to close it
                        response_clean = response_clean[start:]
                        if not response_clean.endswith('}'):
                            response_clean += '}'
                
                # Fix common JSON issues
                response_clean = response_clean.replace('...', '')  # Remove truncation markers
                response_clean = response_clean.replace('"[', '"').replace(']"', '"')  # Fix quoted arrays
                
                analysis = json.loads(response_clean)
                logger.info("✅ AI-powered resume analysis completed successfully")
                return analysis
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parsing failed, falling back to keyword extraction: {e}")
                logger.warning(f"AI Response was: {response[:200]}...")
                # Fallback to basic extraction if AI response isn't valid JSON
                return self._fallback_basic_analysis(text)
                
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            # Fallback to basic extraction
            return self._fallback_basic_analysis(text)
    
    def _fallback_basic_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback to basic keyword-based analysis"""
        text_lower = text.lower()
        
        # Extract basic information using keyword matching
        analysis = {
            "name": "",
            "current_role": "",
            "current_company": "",
            "skills": self._extract_skills(text_lower),
            "experience_years": self._extract_experience_years(text_lower),
            "location": "",
            "industry": ""
        }
        
        return analysis
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from resume"""
        # Common technical skills to look for
        skill_keywords = [
            'python', 'javascript', 'java', 'typescript', 'react', 'nodejs', 'node.js',
            'sql', 'mysql', 'postgresql', 'mongodb', 'nosql', 'aws', 'azure', 'gcp',
            'docker', 'kubernetes', 'git', 'github', 'gitlab', 'ci/cd', 'jenkins',
            'machine learning', 'ml', 'ai', 'artificial intelligence', 'data science',
            'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn', 'flask',
            'django', 'fastapi', 'express', 'angular', 'vue', 'html', 'css',
            'bootstrap', 'rest api', 'graphql', 'microservices', 'agile', 'scrum'
        ]
        
        found_skills = []
        for skill in skill_keywords:
            if skill in text:
                found_skills.append(skill.title())
        
        return list(set(found_skills))  # Remove duplicates
    
    def _extract_experience_years(self, text: str) -> str:
        """Try to extract years of experience"""
        patterns = [
            r'(\d+)\+?\s*years?\s*of\s*experience',
            r'(\d+)\+?\s*years?\s*experience',
            r'(\d+)\+?\s*yrs?\s*experience',
        ]
        
        import re
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                years = int(match.group(1))
                if years <= 1:
                    return "0-1"
                elif years <= 3:
                    return "1-3"
                elif years <= 5:
                    return "3-5"
                elif years <= 8:
                    return "5-8"
                else:
                    return "8+"
        
        return ""
    
    def _extract_education(self, text: str) -> List[str]:
        """Extract education information"""
        education_keywords = [
            'bachelor', 'master', 'phd', 'doctorate', 'degree', 'university',
            'college', 'computer science', 'engineering', 'mathematics', 'physics'
        ]
        
        found_education = []
        for keyword in education_keywords:
            if keyword in text:
                found_education.append(keyword.title())
        
        return list(set(found_education))
    
    def _extract_companies(self, text: str) -> List[str]:
        """Extract company names (simple pattern matching)"""
        # This is a basic implementation - could be enhanced with NER
        lines = text.split('\n')
        companies = []
        
        for line in lines:
            # Look for lines that might contain company info
            if any(word in line.lower() for word in ['software', 'technology', 'inc', 'ltd', 'corp', 'company']):
                companies.append(line.strip())
        
        return companies[:5]  # Return first 5 matches
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract specific technologies mentioned"""
        tech_keywords = [
            'tensorflow', 'pytorch', 'react native', 'flutter', 'android', 'ios',
            'blockchain', 'ethereum', 'redis', 'elasticsearch', 'kafka', 'rabbitmq',
            'nginx', 'apache', 'linux', 'windows', 'macos', 'ubuntu'
        ]
        
        found_tech = []
        for tech in tech_keywords:
            if tech in text:
                found_tech.append(tech.title())
        
        return list(set(found_tech))
    
    def _extract_projects(self, text: str) -> List[str]:
        """Extract project descriptions"""
        # Look for project sections
        lines = text.split('\n')
        projects = []
        
        in_project_section = False
        for line in lines:
            line_lower = line.lower()
            if 'project' in line_lower or 'portfolio' in line_lower:
                in_project_section = True
            elif in_project_section and line.strip():
                if len(line.strip()) > 20:  # Meaningful project description
                    projects.append(line.strip())
                    if len(projects) >= 3:  # Limit to 3 projects
                        break
        
        return projects
    
    def _extract_achievements(self, text: str) -> List[str]:
        """Extract achievements and accomplishments"""
        achievement_indicators = [
            'achieved', 'accomplished', 'improved', 'increased', 'reduced',
            'optimized', 'implemented', 'developed', 'led', 'managed',
            'award', 'recognition', 'promotion'
        ]
        
        lines = text.split('\n')
        achievements = []
        
        for line in lines:
            line_lower = line.lower()
            if any(indicator in line_lower for indicator in achievement_indicators):
                if len(line.strip()) > 30:  # Meaningful achievement
                    achievements.append(line.strip())
                    if len(achievements) >= 5:
                        break
        
        return achievements
    
    def _auto_update_profile_from_resume(self, analysis: Dict[str, Any]) -> None:
        """Auto-update profile fields from resume analysis"""
        # Always update with latest AI analysis (don't preserve old data)
        if analysis.get("name"):
            self.profile_data["personal"]["fullName"] = analysis["name"]
        
        if analysis.get("current_role"):
            self.profile_data["personal"]["currentRole"] = analysis["current_role"]
        
        if analysis.get("current_company"):
            self.profile_data["personal"]["currentCompany"] = analysis["current_company"]
        
        if analysis.get("industry"):
            self.profile_data["personal"]["industry"] = analysis["industry"]
        
        if analysis.get("location"):
            self.profile_data["personal"]["location"] = analysis["location"]
        
        if analysis.get("experience_years"):
            self.profile_data["personal"]["experienceYears"] = analysis["experience_years"]
        
        # Update skills - merge with existing
        if analysis.get("skills"):
            existing_skills = set(self.profile_data["skills"]["selected"])
            new_skills = set(skill.lower() for skill in analysis["skills"] if skill)
            self.profile_data["skills"]["selected"] = list(existing_skills.union(new_skills))
        
        # Update experience fields with more comprehensive data
        if analysis.get("key_projects"):
            self.profile_data["experience"]["keyProjects"] = analysis["key_projects"]
        
        if analysis.get("achievements"):
            self.profile_data["experience"]["achievements"] = analysis["achievements"]
        
        logger.info(f"✅ Auto-populated profile fields from AI resume analysis")
    
    def generate_personalized_prompt(self, question: str) -> str:
        """Generate a personalized prompt based on user profile for ANY interview question"""
        profile = self.get_profile()
        
        # Build detailed context from profile
        personal_info = profile["personal"]
        experience_info = profile["experience"]
        skills_info = profile["skills"]
        
        # Create a rich professional identity
        identity_context = f"""You are {personal_info['fullName']}, a Senior Software Engineer with {personal_info['experienceYears']} of experience currently working at {personal_info['currentCompany']}."""
        
        # Extract specific achievements and quantifiable results
        achievements_context = ""
        if experience_info.get("achievements"):
            achievements_context = f"Your key achievements include: {experience_info['achievements']}"
        
        # Extract specific projects and technologies
        projects_context = ""
        if experience_info.get("keyProjects"):
            projects_context = f"You have extensive experience with: {experience_info['keyProjects']}"
        
        # Get comprehensive skills
        all_skills = skills_info["selected"] + skills_info["additional"]
        technical_expertise = ", ".join(all_skills[:15]) if all_skills else ""
        
        # Get resume details for specific examples
        resume_context = ""
        if profile.get("resume", {}).get("fullText"):
            resume_text = profile["resume"]["fullText"][:2000]  # Use more resume content
            resume_context = f"Drawing from your background: {resume_text}"
        
        # Detect question type and provide specific guidance
        question_lower = question.lower()
        
        question_type = "general"
        specific_instructions = ""
        
        # CODING CHALLENGE DETECTION
        if any(keyword in question_lower for keyword in ["implement", "code", "write a function", "algorithm", "data structure", "lru cache", "binary tree", "linked list", "two sum", "reverse", "palindrome", "fibonacci", "recursive", "iterative", "dynamic programming", "time complexity", "space complexity", "big o"]):
            question_type = "coding_challenge"
            specific_instructions = """
CODING CHALLENGE EXPERTISE: You're a Senior Engineer who can code and explain algorithms clearly. For coding questions:
- Start with clarifying questions about requirements and constraints
- Explain your approach step-by-step before coding
- Write clean, production-ready code with proper variable names
- Explain time and space complexity (Big O notation)
- Discuss trade-offs and optimizations
- Reference your actual coding experience from Oracle Health, ConcertAI projects
- Show how you've implemented similar patterns in production systems

Example approach: "Let me clarify the requirements first... My approach would be... Here's the implementation... Time complexity is O(n), Space is O(1)... In production at Oracle Health, I used a similar pattern when..."
"""
        
        # SYSTEM DESIGN DETECTION  
        elif any(keyword in question_lower for keyword in ["design", "architect", "scale", "distributed", "microservices", "load balancer", "database design", "api design", "instagram", "facebook", "twitter", "uber", "netflix", "chat system", "messaging", "notification", "feed", "search engine", "million users", "high availability", "consistency", "partition tolerance"]):
            question_type = "system_design"
            specific_instructions = """
SYSTEM DESIGN EXPERTISE: You've architected healthcare systems at scale. For system design questions:
- Start with requirements gathering and scale estimation
- Break down into high-level components first
- Deep dive into specific components (API layer, database, caching, etc.)
- Discuss scalability, reliability, and consistency trade-offs
- Reference your actual system design experience from Oracle Health and ConcertAI
- Show how you've handled similar problems in production (supporting 100+ users, 30% performance improvements, etc.)
- Discuss monitoring, deployment, and operational concerns

Example approach: "Let me understand the requirements... For X million users, we'd need... I've built similar systems at Oracle Health where we handled..."
"""
        
        # BEHAVIORAL DETECTION
        elif any(keyword in question_lower for keyword in ["time when", "situation where", "experience with", "example of", "disagreed", "conflict", "challenge", "difficult", "problem", "failed", "mistake", "wrong", "error", "led a team", "managed", "leadership", "mentoring", "proud of", "achievement", "success", "accomplished", "tell me about a project", "describe a situation"]):
            question_type = "behavioral"
            specific_instructions = """
BEHAVIORAL LEADERSHIP EXPERIENCE: You're a Senior Engineer with 8+ years across multiple companies. For behavioral questions:
- Use the STAR method (Situation, Task, Action, Result) with specific examples
- Draw from your actual experience progression: American Express → NIH → Comcast → ConcertAI → Oracle Health
- Show leadership growth over 8+ years
- Include specific business impact and metrics (30% improvements, 100+ users, etc.)
- Demonstrate senior-level problem-solving and decision-making
- Show how you've mentored others and influenced team decisions
- Reference actual challenges in healthcare domain, fintech, enterprise systems

Example approach: "At ConcertAI, I faced a situation where... The challenge was... I took the approach of... The result was a 30% improvement in..."
"""
        
        # PRODUCT/BUSINESS DETECTION
        elif any(keyword in question_lower for keyword in ["improve", "optimize", "feature", "product", "user experience", "metrics", "analytics", "data", "growth", "engagement", "strategy", "roadmap", "priority", "decision", "trade-off", "customer", "user", "business", "market", "competition", "facebook", "meta", "instagram"]):
            question_type = "product"
            specific_instructions = """
PRODUCT & BUSINESS IMPACT: You've delivered measurable business value through technology. For product questions:
- Think like a senior engineer who understands business impact
- Reference your healthcare domain expertise and user-focused solutions
- Show how technical decisions drive business outcomes
- Discuss data-driven decision making and metrics
- Reference your experience supporting 100+ daily users with secure systems
- Show understanding of user needs in regulated industries (healthcare, fintech)
- Demonstrate how you've collaborated with product managers and stakeholders

Example approach: "Based on my experience at Oracle Health supporting healthcare applications... I'd approach this by first understanding the user pain points... The technical solution would involve... This would impact business metrics by..."
"""
        
        # TECHNICAL DEEP DIVE DETECTION
        elif any(keyword in question_lower for keyword in ["technical", "programming", "software engineering", "code review", "testing", "deployment", "monitoring", "debugging", "performance", "optimization", "security", "database", "api", "framework", "language", "java", "python", "javascript", "spring boot", "react", "aws", "docker", "kubernetes"]):
            question_type = "technical_deep_dive"
            specific_instructions = """
TECHNICAL DEEP DIVE EXPERTISE: You're a Senior Engineer with hands-on experience across the full stack. For technical questions:
- Demonstrate deep knowledge of your actual tech stack (Java Spring Boot, React, AWS, Docker, Kubernetes)
- Reference specific technical decisions you've made in production
- Show understanding of enterprise-grade concerns (security, scalability, maintainability)
- Discuss technical trade-offs with business considerations
- Reference your experience with healthcare compliance and security requirements
- Show progression in technical complexity across your 8+ year career

Example approach: "In my experience at Oracle Health, when dealing with similar technical challenges... I chose Java Spring Boot because... The trade-offs were... This resulted in..."
"""
        
        else:
            # GENERAL META-STYLE INTERVIEW QUESTION
            specific_instructions = """
SENIOR ENGINEER INTERVIEW EXCELLENCE: You're interviewing for a senior role at a top tech company. For any question:
- Demonstrate IC4/IC5 level thinking with business and technical depth
- Use specific examples from your 8+ years of experience
- Show progression across companies: American Express → NIH → Comcast → ConcertAI → Oracle Health
- Reference quantifiable achievements and business impact
- Show leadership, mentoring, and cross-functional collaboration
- Demonstrate learning from failures and continuous improvement
- Connect technical solutions to business value
"""
        
        # Communication style preferences
        style = profile["preferences"]["communicationStyle"]
        personality_instructions = {
            "confident": "Speak with senior-level confidence and authority. Use strong action verbs. Show thought leadership.",
            "thoughtful": "Provide thoughtful, analytical responses showing architectural thinking and strategic considerations.", 
            "conversational": "Be engaging while demonstrating deep technical expertise and business acumen.",
            "technical": "Use precise technical language demonstrating IC4/IC5 level depth and breadth.",
            "concise": "Be direct and impactful, showing senior engineer decision-making skills."
        }
        
        # Build the comprehensive prompt for any question type
        prompt = f"""You are {personal_info['fullName']} in a senior software engineer (IC4/IC5/E5/E6 level) interview. You must respond as this specific person with their exact background and achievements.

PROFESSIONAL IDENTITY:
{identity_context}

SPECIFIC EXPERIENCE & ACHIEVEMENTS:
{achievements_context}

TECHNICAL EXPERTISE & PROJECTS:
{projects_context}
Technical skills: {technical_expertise}

BACKGROUND DETAILS:
{resume_context}

QUESTION TYPE: {question_type.upper()}
{specific_instructions}

INTERVIEW QUESTION: "{question}"

SENIOR-LEVEL RESPONSE REQUIREMENTS:
1. {personality_instructions.get(style, "Speak with confidence and senior-level professionalism")}
2. Use SPECIFIC examples from your actual experience (Oracle Health lab systems, ConcertAI data pipelines, etc.)
3. Include quantifiable results and business impact (30% improvements, 100+ users, etc.)
4. Demonstrate IC4/IC5 level thinking: architectural decisions, trade-offs, business considerations
5. Reference specific technologies from your stack: Java Spring Boot, React, AWS, Docker, Kubernetes, etc.
6. Show progression from American Express → NIH → Comcast → ConcertAI → Oracle Health
7. For system design: Reference your microservices, healthcare compliance, scaling experience
8. For coding: Use your actual tech stack and real problem-solving experience
9. For behavioral: Draw from your 8+ years across multiple companies and domains
10. For product: Show how your technical decisions drove business outcomes
11. Sound like a senior engineer who has solved complex problems at enterprise scale
12. Never mention AI assistance - respond as the actual person
13. Use "I" statements with confidence befitting your experience level
14. Show depth of knowledge appropriate for senior IC roles

Respond as {personal_info['fullName']} would, demonstrating senior-level expertise and drawing from their specific 8+ years of experience across healthcare, fintech, and enterprise systems."""

        return prompt
    
    def test_personalization(self, test_questions: List[str]) -> List[Dict[str, str]]:
        """Test personalized responses for given questions"""
        examples = []
        
        for question in test_questions:
            # This would normally call the AI service, but for testing we'll create a mock response
            personalized_prompt = self.generate_personalized_prompt(question)
            
            # Mock response based on profile
            profile = self.get_profile()
            
            if "about yourself" in question.lower():
                response = self._generate_about_response(profile)
            elif "experience" in question.lower() or "python" in question.lower():
                response = self._generate_experience_response(profile, question)
            elif "project" in question.lower() or "challenging" in question.lower():
                response = self._generate_project_response(profile)
            else:
                response = self._generate_generic_response(profile, question)
            
            examples.append({
                "question": question,
                "answer": response,
                "prompt_used": personalized_prompt[:200] + "..."
            })
        
        return examples
    
    def _generate_about_response(self, profile: Dict) -> str:
        """Generate 'about yourself' response based on profile"""
        name = profile["personal"]["fullName"] or "I"
        role = profile["personal"]["currentRole"] or "a professional"
        company = profile["personal"]["currentCompany"]
        skills = profile["skills"]["selected"][:3]
        
        response = f"I'm {name}, currently working as {role}"
        if company:
            response += f" at {company}"
        
        if skills:
            response += f". I specialize in {', '.join(skills)}"
        
        response += ". I'm passionate about solving complex problems and delivering high-quality solutions."
        
        return response
    
    def _generate_experience_response(self, profile: Dict, question: str) -> str:
        """Generate experience-based response"""
        exp_years = profile["personal"]["experienceYears"]
        skills = profile["skills"]["selected"] + profile["skills"]["additional"]
        
        if "python" in question.lower() and "python" in [s.lower() for s in skills]:
            return f"I have {exp_years.replace('-', ' to ')} years of experience with Python. I've used it extensively for web development, data analysis, and automation projects. I'm comfortable with frameworks like Django and Flask."
        
        return f"I have {exp_years.replace('-', ' to ')} years of experience in software development, working with technologies like {', '.join(skills[:4])}. I've been involved in full-stack development and enjoy tackling both frontend and backend challenges."
    
    def _generate_project_response(self, profile: Dict) -> str:
        """Generate project-based response"""
        projects = profile["experience"]["keyProjects"]
        if projects:
            return f"One of my most challenging projects involved {projects[:100]}... This required me to solve complex technical problems and collaborate effectively with the team."
        
        return "I recently worked on a challenging project that required optimizing performance and scalability. I had to research new technologies, implement innovative solutions, and coordinate with multiple stakeholders to deliver on time."
    
    def _generate_generic_response(self, profile: Dict, question: str) -> str:
        """Generate generic professional response"""
        style = profile["preferences"]["communicationStyle"]
        
        if style == "confident":
            return "I'm confident in my ability to handle this type of challenge. Based on my experience, I would approach it systematically and leverage my technical skills to find the best solution."
        elif style == "thoughtful":
            return "That's an interesting question. I would need to consider various factors and analyze the requirements carefully before proposing a solution that balances efficiency and maintainability."
        else:
            return "I believe my background and experience make me well-suited for this. I enjoy taking on new challenges and I'm always eager to learn and apply new technologies."


# Export the main class
__all__ = ['ProfileManager']
