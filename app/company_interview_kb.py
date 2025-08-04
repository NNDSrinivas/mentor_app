"""
Company-specific interview knowledge base and patterns.
Contains curated questions, responses, and strategies for top tech companies.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from .knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

@dataclass
class InterviewPattern:
    """Interview pattern for a specific company or type."""
    company: str
    question_type: str  # behavioral, technical, system_design, product
    pattern: str
    example_questions: List[str]
    response_framework: str
    key_points: List[str]
    common_followups: List[str]

@dataclass
class CompanyProfile:
    """Profile of a company's interview style and culture."""
    name: str
    values: List[str]
    interview_style: str
    technical_focus: List[str]
    behavioral_themes: List[str]
    difficulty_level: str
    typical_rounds: List[str]
    leadership_principles: List[str]

class CompanyInterviewKB:
    """Knowledge base for company-specific interview preparation."""
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.companies = {}
        self.patterns = {}
        self.system_design_patterns = {}
        self.behavioral_frameworks = {}
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with company data."""
        
        # Define company profiles
        self._load_company_profiles()
        
        # Load interview patterns
        self._load_interview_patterns()
        
        # Load system design patterns
        self._load_system_design_patterns()
        
        # Load behavioral frameworks
        self._load_behavioral_frameworks()
        
        logger.info("✅ Company interview knowledge base initialized")
    
    def _load_company_profiles(self):
        """Load company profiles and culture information."""
        
        self.companies = {
            "Meta": CompanyProfile(
                name="Meta",
                values=["Move Fast", "Be Bold", "Focus on Impact", "Be Open", "Build Social Value"],
                interview_style="Behavioral + Technical depth, Focus on impact and scale",
                technical_focus=["Distributed Systems", "Machine Learning", "Mobile", "Web", "Infra"],
                behavioral_themes=["Impact", "Collaboration", "Innovation", "Speed", "Decision Making"],
                difficulty_level="High",
                typical_rounds=["Phone Screen", "Technical Onsite", "Behavioral", "System Design"],
                leadership_principles=["Move Fast", "Be Bold", "Focus on Impact", "Be Open"]
            ),
            
            "Google": CompanyProfile(
                name="Google",
                values=["Focus on the user", "Think big", "Launch and iterate", "Be original"],
                interview_style="Algorithmic thinking + System design + Behavioral",
                technical_focus=["Algorithms", "Data Structures", "System Design", "ML", "Distributed Systems"],
                behavioral_themes=["Leadership", "Problem Solving", "Innovation", "Collaboration"],
                difficulty_level="Very High",
                typical_rounds=["Phone Screen", "Technical Onsite (4-5 rounds)", "Behavioral"],
                leadership_principles=["Googleyness", "Leadership", "Role-related Knowledge", "General Cognitive Ability"]
            ),
            
            "Amazon": CompanyProfile(
                name="Amazon",
                values=["Customer Obsession", "Ownership", "Invent and Simplify", "Deliver Results"],
                interview_style="Strong focus on Leadership Principles + Technical competency",
                technical_focus=["Distributed Systems", "Scalability", "Cost Optimization", "Operations"],
                behavioral_themes=["Customer Focus", "Ownership", "Bias for Action", "Frugality"],
                difficulty_level="High",
                typical_rounds=["Phone Screen", "Technical Onsite", "Behavioral (LP Focus)", "System Design"],
                leadership_principles=[
                    "Customer Obsession", "Ownership", "Invent and Simplify", "Are Right, A Lot",
                    "Learn and Be Curious", "Hire and Develop the Best", "Insist on the Highest Standards",
                    "Think Big", "Bias for Action", "Frugality", "Earn Trust", "Dive Deep",
                    "Have Backbone; Disagree and Commit", "Deliver Results", "Strive to be Earth's Best Employer"
                ]
            ),
            
            "Microsoft": CompanyProfile(
                name="Microsoft",
                values=["Respect", "Integrity", "Accountability", "Inclusive Culture"],
                interview_style="Collaborative problem solving + Technical depth",
                technical_focus=["Cloud Computing", "Enterprise Software", "Developer Tools", "AI"],
                behavioral_themes=["Growth Mindset", "Collaboration", "Diversity", "Innovation"],
                difficulty_level="Medium-High",
                typical_rounds=["Phone Screen", "Technical Onsite", "Behavioral", "Design Discussion"],
                leadership_principles=["Growth Mindset", "Customer Focus", "Partner for Success", "Inclusion"]
            ),
            
            "Apple": CompanyProfile(
                name="Apple",
                values=["Innovation", "Excellence", "Simplicity", "Privacy"],
                interview_style="Product focus + Technical excellence + Cultural fit",
                technical_focus=["iOS/macOS", "Hardware-Software Integration", "Performance", "UX"],
                behavioral_themes=["Innovation", "Attention to Detail", "Collaboration", "Excellence"],
                difficulty_level="High",
                typical_rounds=["Phone Screen", "Technical Deep Dive", "Product Discussion", "Cultural Fit"],
                leadership_principles=["Think Different", "Simplicity", "Excellence", "Innovation"]
            ),
            
            "Netflix": CompanyProfile(
                name="Netflix",
                values=["Judgment", "Communication", "Curiosity", "Courage", "Passion", "Selflessness", "Innovation", "Inclusion", "Integrity", "Impact"],
                interview_style="High performance culture + Technical excellence",
                technical_focus=["Streaming Technology", "Data Science", "Cloud Infrastructure", "Personalization"],
                behavioral_themes=["High Performance", "Freedom & Responsibility", "Context over Control"],
                difficulty_level="Very High",
                typical_rounds=["Phone Screen", "Technical Excellence", "Cultural Values", "System Design"],
                leadership_principles=["Keeper Test", "Freedom & Responsibility", "High Performance", "Context not Control"]
            )
        }
    
    def _load_interview_patterns(self):
        """Load common interview patterns for each company."""
        
        self.patterns = {
            "Meta_Behavioral": InterviewPattern(
                company="Meta",
                question_type="behavioral",
                pattern="STAR method with impact focus",
                example_questions=[
                    "Tell me about a time you had to make a decision with incomplete information",
                    "Describe a project where you had to move fast and break things",
                    "How did you handle a situation where you disagreed with your manager?",
                    "Tell me about a time you took on something outside your comfort zone",
                    "Describe your most significant technical achievement"
                ],
                response_framework="Situation + Task + Action + Result + Impact/Learning",
                key_points=["Scale/Impact", "Speed of execution", "Data-driven decisions", "Cross-functional collaboration"],
                common_followups=["How did you measure success?", "What would you do differently?", "How did this impact the business?"]
            ),
            
            "Meta_Technical": InterviewPattern(
                company="Meta",
                question_type="technical",
                pattern="Algorithm + System Design + Production considerations",
                example_questions=[
                    "Design a news feed ranking system",
                    "How would you detect fake accounts at scale?",
                    "Design a chat system for 1 billion users",
                    "Implement a rate limiter for API calls",
                    "Design a system to handle video uploads and encoding"
                ],
                response_framework="Requirements + Scale + Architecture + Trade-offs + Monitoring",
                key_points=["Scalability", "Real-time processing", "Data consistency", "Performance optimization"],
                common_followups=["How would you handle failures?", "How would you scale this?", "What metrics would you track?"]
            ),
            
            "Google_Technical": InterviewPattern(
                company="Google",
                question_type="technical",
                pattern="Algorithm optimization + Clean code + Edge cases",
                example_questions=[
                    "Find the shortest path in a maze",
                    "Design autocomplete for Google Search",
                    "Implement a LRU cache with O(1) operations",
                    "Design a web crawler for the entire internet",
                    "How would you design Google Photos?"
                ],
                response_framework="Understand + Plan + Code + Test + Optimize",
                key_points=["Algorithmic efficiency", "Code quality", "Edge case handling", "Optimization"],
                common_followups=["Can you optimize this further?", "How would you test this?", "What's the time complexity?"]
            ),
            
            "Amazon_Leadership": InterviewPattern(
                company="Amazon",
                question_type="behavioral",
                pattern="Leadership Principles with specific examples",
                example_questions=[
                    "Tell me about a time you had to make a decision with limited data (Are Right, A Lot)",
                    "Describe a time you went above and beyond for a customer (Customer Obsession)",
                    "Tell me about a time you had to learn something completely new (Learn and Be Curious)",
                    "Describe a situation where you had to deliver results under pressure (Deliver Results)",
                    "Tell me about a time you simplified a complex process (Invent and Simplify)"
                ],
                response_framework="STAR + Leadership Principle demonstration",
                key_points=["Customer impact", "Ownership mindset", "Data-driven decisions", "Long-term thinking"],
                common_followups=["How did this benefit the customer?", "What was your role specifically?", "How did you measure success?"]
            )
        }
    
    def _load_system_design_patterns(self):
        """Load system design patterns and approaches."""
        
        self.system_design_patterns = {
            "social_media": {
                "title": "Social Media Feed Design",
                "companies": ["Meta", "Twitter", "LinkedIn"],
                "key_components": ["User Service", "Post Service", "Feed Generation", "Notification Service"],
                "scale_considerations": ["Billions of users", "Real-time updates", "Personalization", "Global distribution"],
                "technologies": ["Redis", "Kafka", "Cassandra", "CDN", "Machine Learning"],
                "challenges": ["Hot celebrities", "Spam detection", "Real-time ranking", "Storage optimization"]
            },
            
            "search_engine": {
                "title": "Search Engine Design",
                "companies": ["Google", "Microsoft", "Amazon"],
                "key_components": ["Web Crawler", "Indexer", "Ranker", "Query Processor"],
                "scale_considerations": ["Petabytes of data", "Millisecond latency", "Global infrastructure"],
                "technologies": ["Distributed Storage", "MapReduce", "Machine Learning", "CDN"],
                "challenges": ["Freshness", "Relevance", "Spam", "Personalization"]
            },
            
            "video_streaming": {
                "title": "Video Streaming Platform",
                "companies": ["Netflix", "YouTube", "Amazon Prime"],
                "key_components": ["Upload Service", "Encoding Service", "CDN", "Recommendation Engine"],
                "scale_considerations": ["Millions of concurrent users", "Global distribution", "Multiple formats"],
                "technologies": ["CDN", "Adaptive Bitrate Streaming", "Machine Learning", "Microservices"],
                "challenges": ["Bandwidth optimization", "Content delivery", "Personalization", "Cost optimization"]
            }
        }
    
    def _load_behavioral_frameworks(self):
        """Load behavioral interview frameworks."""
        
        self.behavioral_frameworks = {
            "STAR": {
                "name": "Situation, Task, Action, Result",
                "structure": [
                    "Situation: Set the context",
                    "Task: Describe your responsibility", 
                    "Action: Explain what you did",
                    "Result: Share the outcome"
                ],
                "tips": [
                    "Be specific with numbers and metrics",
                    "Focus on your individual contribution",
                    "Highlight the impact and learning",
                    "Choose recent, relevant examples"
                ]
            },
            
            "CARL": {
                "name": "Context, Action, Result, Learning",
                "structure": [
                    "Context: Background situation",
                    "Action: What you specifically did",
                    "Result: Outcome achieved", 
                    "Learning: What you learned"
                ],
                "tips": [
                    "Emphasize personal growth",
                    "Show continuous improvement",
                    "Connect to future applications"
                ]
            }
        }
    
    def get_company_questions(self, company: str, question_type: str = None) -> List[str]:
        """Get questions for a specific company and type."""
        
        questions = []
        for pattern_key, pattern in self.patterns.items():
            if pattern.company == company:
                if question_type is None or pattern.question_type == question_type:
                    questions.extend(pattern.example_questions)
        
        return questions
    
    def get_response_framework(self, company: str, question_type: str) -> Optional[InterviewPattern]:
        """Get response framework for company and question type."""
        
        pattern_key = f"{company}_{question_type.title()}"
        return self.patterns.get(pattern_key)
    
    def generate_company_specific_response(self, company: str, question: str, user_context: Dict) -> str:
        """Generate a company-specific response to an interview question."""
        
        company_profile = self.companies.get(company)
        if not company_profile:
            return self._generate_generic_response(question, user_context)
        
        # Determine question type
        question_type = self._classify_question(question)
        
        # Get response framework
        framework = self.get_response_framework(company, question_type)
        
        # Build response prompt
        prompt = self._build_company_response_prompt(
            company, question, question_type, framework, user_context
        )
        
        return prompt
    
    def _classify_question(self, question: str) -> str:
        """Classify the type of interview question."""
        
        question_lower = question.lower()
        
        # Behavioral indicators
        behavioral_keywords = ["tell me about a time", "describe a situation", "how did you handle", "give me an example"]
        if any(keyword in question_lower for keyword in behavioral_keywords):
            return "behavioral"
        
        # System design indicators
        design_keywords = ["design", "architecture", "scale", "system", "how would you build"]
        if any(keyword in question_lower for keyword in design_keywords):
            return "system_design"
        
        # Technical/coding indicators
        technical_keywords = ["implement", "algorithm", "code", "solve", "optimize"]
        if any(keyword in question_lower for keyword in technical_keywords):
            return "technical"
        
        # Product indicators
        product_keywords = ["product", "feature", "user", "customer", "metrics"]
        if any(keyword in question_lower for keyword in product_keywords):
            return "product"
        
        return "general"
    
    def _build_company_response_prompt(self, company: str, question: str, 
                                     question_type: str, framework: Optional[InterviewPattern], 
                                     user_context: Dict) -> str:
        """Build a company-specific response prompt."""
        
        company_profile = self.companies[company]
        
        prompt = f"You are interviewing for a senior engineering role at {company}.\n\n"
        prompt += f"COMPANY CONTEXT:\n"
        prompt += f"- Values: {', '.join(company_profile.values)}\n"
        prompt += f"- Interview Style: {company_profile.interview_style}\n"
        prompt += f"- Technical Focus: {', '.join(company_profile.technical_focus)}\n"
        
        if company_profile.leadership_principles:
            prompt += f"- Key Principles: {', '.join(company_profile.leadership_principles[:4])}\n"
        
        prompt += f"\nQUESTION: {question}\n\n"
        
        if framework:
            prompt += f"RESPONSE FRAMEWORK ({framework.response_framework}):\n"
            for point in framework.key_points:
                prompt += f"- {point}\n"
        
        prompt += f"\nAnswer as a senior engineer with these guidelines:\n"
        prompt += f"1. Demonstrate alignment with {company}'s values\n"
        prompt += f"2. Show understanding of scale and complexity\n"
        prompt += f"3. Use specific technical examples\n"
        prompt += f"4. Highlight leadership and impact\n"
        prompt += f"5. Keep response under 2 minutes (300-400 words)\n"
        
        if question_type == "behavioral" and company == "Amazon":
            prompt += f"6. Clearly demonstrate an Amazon Leadership Principle\n"
        elif question_type == "behavioral" and company == "Meta":
            prompt += f"6. Focus on impact and moving fast with incomplete information\n"
        
        return prompt
    
    def _generate_generic_response(self, question: str, user_context: Dict) -> str:
        """Generate a generic response when company-specific data isn't available."""
        
        return f"For the question '{question}', I would focus on demonstrating senior-level technical expertise, leadership experience, and quantifiable impact. Let me structure my response using the STAR method to provide specific examples from my experience."
    
    def add_custom_pattern(self, pattern: InterviewPattern):
        """Add a custom interview pattern to the knowledge base."""
        
        pattern_key = f"{pattern.company}_{pattern.question_type}"
        self.patterns[pattern_key] = pattern
        
        # Add to vector knowledge base for retrieval
        content = f"Company: {pattern.company}\nType: {pattern.question_type}\nPattern: {pattern.pattern}\nQuestions: {'; '.join(pattern.example_questions)}"
        
        metadata = {
            "type": "interview_pattern",
            "company": pattern.company,
            "question_type": pattern.question_type
        }
        
        self.kb.add_document(content, metadata)
        logger.info(f"✅ Added custom pattern for {pattern.company} {pattern.question_type}")
    
    def search_similar_questions(self, question: str, company: str = None) -> List[Dict]:
        """Search for similar questions in the knowledge base."""
        
        # Build search query
        search_text = f"interview question: {question}"
        if company:
            search_text += f" company: {company}"
        
        try:
            results = self.kb.search(search_text, top_k=5)
            return results
        except Exception as e:
            logger.error(f"Error searching similar questions: {e}")
            return []
    
    def get_interview_tips(self, company: str, role_level: str = "senior") -> Dict[str, List[str]]:
        """Get interview tips specific to a company and role level."""
        
        company_profile = self.companies.get(company)
        if not company_profile:
            return {"general": ["Focus on technical depth", "Demonstrate leadership", "Show impact"]}
        
        tips = {
            "preparation": [
                f"Study {company}'s values: {', '.join(company_profile.values[:3])}",
                f"Understand their technical focus: {', '.join(company_profile.technical_focus[:3])}",
                "Prepare STAR method examples with quantified impact",
                "Practice system design for their scale"
            ],
            "technical": [
                "Focus on scalability and performance",
                "Discuss trade-offs and alternatives", 
                "Show production experience",
                "Demonstrate debugging skills"
            ],
            "behavioral": [
                f"Align examples with {company}'s behavioral themes",
                "Emphasize leadership and cross-functional collaboration",
                "Show data-driven decision making",
                "Highlight customer/user impact"
            ]
        }
        
        # Add company-specific tips
        if company == "Amazon":
            tips["behavioral"].append("Map each story to specific Leadership Principles")
        elif company == "Meta":
            tips["behavioral"].append("Emphasize moving fast and learning from failures")
        elif company == "Google":
            tips["technical"].append("Focus on algorithmic efficiency and clean code")
        
        return tips
