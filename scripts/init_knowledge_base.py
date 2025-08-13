"""
Initialize Knowledge Base with Interview-Relevant Content
Populates the knowledge base with technical concepts, interview tips, and company-specific information
"""
import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.knowledge_base import KnowledgeBase

def initialize_knowledge_base():
    """Initialize knowledge base with comprehensive interview content"""
    
    print("🚀 Initializing AI Mentor Knowledge Base...")
    
    try:
        kb = KnowledgeBase()
        print(f"✅ Knowledge base connected: {kb.get_collection_info()}")
    except Exception as e:
        print(f"❌ Failed to connect to knowledge base: {e}")
        return
    
    # Technical Concepts Knowledge
    technical_concepts = [
        {
            "title": "Microservices Architecture",
            "content": """
Microservices architecture is a design approach where applications are built as a collection of loosely coupled, independently deployable services. Each service is responsible for a specific business capability and communicates with other services through well-defined APIs.

Key Benefits:
- Independent scaling of services based on demand
- Technology diversity - each service can use different tech stacks
- Fault isolation - failure in one service doesn't bring down the entire system
- Faster development cycles with smaller, focused teams
- Better alignment with DevOps practices

Key Challenges:
- Increased complexity in service coordination and management
- Network latency and communication overhead
- Data consistency across services
- Monitoring and debugging distributed systems
- Service discovery and load balancing complexity

Best Practices:
- Design services around business capabilities
- Implement proper API versioning
- Use circuit breakers for fault tolerance
- Implement centralized logging and monitoring
- Design for failure from the beginning
            """,
            "type": "technical_concept",
            "category": "system_design",
            "difficulty": "intermediate"
        },
        {
            "title": "System Design - Database Sharding",
            "content": """
Database sharding is a database architecture pattern where data is horizontally partitioned across multiple database instances. Each shard contains a subset of the total data, distributed according to a sharding strategy.

Sharding Strategies:
1. Range-based sharding: Data distributed based on ranges of values
2. Hash-based sharding: Uses hash function to determine shard placement
3. Directory-based sharding: Uses lookup service to determine data location
4. Geographic sharding: Data distributed based on geographic regions

Benefits:
- Improved query performance through parallel processing
- Enhanced scalability for large datasets
- Better resource utilization across multiple servers
- Increased availability - single shard failures don't affect entire system

Challenges:
- Increased complexity in application logic
- Cross-shard queries can be expensive
- Rebalancing shards as data grows
- Maintaining data consistency across shards
- Hotspot management when some shards receive more traffic

Considerations for Implementation:
- Choose appropriate shard key to ensure even distribution
- Plan for future rebalancing needs
- Implement proper monitoring for shard health
- Design application to handle shard failures gracefully
            """,
            "type": "technical_concept",
            "category": "database",
            "difficulty": "advanced"
        },
        {
            "title": "RESTful API Design Principles",
            "content": """
REST (Representational State Transfer) is an architectural style for designing networked applications. RESTful APIs follow specific principles to ensure scalability, simplicity, and interoperability.

Core Principles:
1. Stateless: Each request contains all information needed to process it
2. Client-Server: Clear separation between client and server responsibilities
3. Cacheable: Responses should be cacheable when appropriate
4. Uniform Interface: Consistent interface between components
5. Layered System: Architecture composed of hierarchical layers

HTTP Methods and Usage:
- GET: Retrieve data (idempotent, safe)
- POST: Create new resources
- PUT: Update/replace entire resource (idempotent)
- PATCH: Partial updates to resources
- DELETE: Remove resources (idempotent)

Best Practices:
- Use nouns for resource URLs, not verbs
- Implement proper HTTP status codes (200, 201, 400, 404, 500, etc.)
- Version your APIs (/v1/users, /v2/users)
- Use consistent naming conventions
- Implement proper error handling with meaningful messages
- Include pagination for large datasets
- Use HTTPS for security
- Implement proper authentication and authorization

Common HTTP Status Codes:
- 200 OK: Successful GET, PUT, PATCH
- 201 Created: Successful POST
- 204 No Content: Successful DELETE
- 400 Bad Request: Invalid request syntax
- 401 Unauthorized: Authentication required
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Resource doesn't exist
- 500 Internal Server Error: Server-side error
            """,
            "type": "technical_concept",
            "category": "api_design",
            "difficulty": "intermediate"
        },
        {
            "title": "Data Structures - Time and Space Complexity",
            "content": """
Understanding time and space complexity is crucial for writing efficient algorithms and choosing appropriate data structures.

Big O Notation:
- O(1): Constant time - operations take same time regardless of input size
- O(log n): Logarithmic time - time increases logarithmically with input
- O(n): Linear time - time increases linearly with input size
- O(n log n): Linearithmic time - common in efficient sorting algorithms
- O(n²): Quadratic time - nested loops over input
- O(2^n): Exponential time - avoid for large inputs

Common Data Structures and Complexities:

Arrays:
- Access: O(1)
- Search: O(n)
- Insertion: O(n) - worst case at beginning
- Deletion: O(n) - worst case at beginning

Hash Tables:
- Access: N/A
- Search: O(1) average, O(n) worst case
- Insertion: O(1) average, O(n) worst case
- Deletion: O(1) average, O(n) worst case

Binary Search Trees:
- Access: O(log n) average, O(n) worst case
- Search: O(log n) average, O(n) worst case
- Insertion: O(log n) average, O(n) worst case
- Deletion: O(log n) average, O(n) worst case

Linked Lists:
- Access: O(n)
- Search: O(n)
- Insertion: O(1) at head, O(n) at arbitrary position
- Deletion: O(1) at head, O(n) at arbitrary position

Interview Tips:
- Always discuss both time and space complexity
- Consider average vs worst-case scenarios
- Think about trade-offs between time and space
- Mention when certain complexities are acceptable based on use case
            """,
            "type": "technical_concept",
            "category": "algorithms",
            "difficulty": "fundamental"
        }
    ]
    
    # Interview Tips and Strategies
    interview_strategies = [
        {
            "title": "System Design Interview Strategy",
            "content": """
System design interviews assess your ability to design large-scale distributed systems. Here's a structured approach:

1. Clarify Requirements (5-10 minutes):
   - Functional requirements: What features does the system need?
   - Non-functional requirements: Scale, performance, reliability
   - Constraints: Budget, time, existing technology stack
   - Assumptions: Traffic patterns, data size, geographic distribution

2. High-Level Design (10-15 minutes):
   - Start with simple design showing major components
   - Identify main services/modules
   - Show data flow between components
   - Don't dive into details yet

3. Deep Dive (15-20 minutes):
   - Database design and data models
   - API design for key services
   - Detailed component architecture
   - Address specific technical challenges

4. Scale and Optimize (10-15 minutes):
   - Identify bottlenecks
   - Discuss scaling strategies
   - Add caching layers
   - Consider load balancing and redundancy
   - Discuss monitoring and alerting

Key Tips:
- Ask clarifying questions throughout
- Think out loud - show your thought process
- Start simple and add complexity gradually
- Discuss trade-offs explicitly
- Be prepared to defend your design choices
- Know when to use SQL vs NoSQL databases
- Understand CAP theorem implications
- Consider security aspects

Common Pitfalls to Avoid:
- Jumping into details too quickly
- Not asking enough clarifying questions
- Overengineering the initial solution
- Ignoring non-functional requirements
- Not considering failure scenarios
            """,
            "type": "interview_strategy",
            "category": "system_design",
            "difficulty": "intermediate"
        },
        {
            "title": "Behavioral Interview - STAR Method",
            "content": """
The STAR method provides a structured way to answer behavioral interview questions by telling compelling stories that demonstrate your skills and experience.

STAR Framework:
- Situation: Set the context and background
- Task: Describe your responsibility or challenge
- Action: Explain the specific actions you took
- Result: Share the outcomes and what you learned

Example Question: "Tell me about a time you had to work with a difficult team member."

STAR Response:
Situation: "In my previous role as a senior engineer, I was leading a team of 5 developers on a critical project with a tight deadline. One team member consistently missed meetings, delivered work late, and wasn't communicating blockers effectively."

Task: "As the tech lead, I needed to address this situation while maintaining team morale and ensuring we met our project deadline. I also wanted to understand if there were underlying issues affecting their performance."

Action: "I scheduled a private one-on-one meeting with the team member to understand their perspective. I discovered they were overwhelmed with personal issues and struggling with some of the newer technologies we were using. I worked with them to create a support plan: I paired them with a mentor for the technical challenges, adjusted their workload temporarily, and established daily check-ins to ensure they felt supported."

Result: "Over the next few weeks, their performance improved significantly. They started communicating more effectively and meeting deadlines. The project was completed on time, and the team member later thanked me for the support during a difficult period. I learned the importance of addressing performance issues with empathy and seeking to understand root causes."

Tips for Strong STAR Responses:
- Choose examples that highlight relevant skills
- Be specific with numbers and timelines when possible
- Focus on YOUR actions, not what the team did
- Emphasize positive outcomes and lessons learned
- Practice 4-5 strong STAR stories covering different competencies
- Keep responses concise (2-3 minutes maximum)

Common Behavioral Question Categories:
- Leadership and influence
- Problem-solving and analytical thinking
- Dealing with ambiguity and change
- Collaboration and teamwork
- Customer focus and impact
- Learning and growth mindset
            """,
            "type": "interview_strategy",
            "category": "behavioral",
            "difficulty": "fundamental"
        }
    ]
    
    # Add all content to knowledge base
    all_content = technical_concepts + interview_strategies
    
    print(f"📚 Adding {len(all_content)} knowledge documents...")
    
    added_count = 0
    for item in all_content:
        try:
            doc_id = kb.add_document(
                content=item["content"],
                metadata={
                    "title": item["title"],
                    "type": item["type"],
                    "category": item["category"],
                    "difficulty": item["difficulty"],
                    "source": "initialization",
                    "curated": True
                }
            )
            print(f"✅ Added: {item['title']} (ID: {doc_id[:8]}...)")
            added_count += 1
        except Exception as e:
            print(f"❌ Failed to add {item['title']}: {e}")
    
    print(f"🎉 Knowledge base initialization complete!")
    print(f"📊 Added {added_count}/{len(all_content)} documents")
    
    # Show final statistics
    final_stats = kb.get_collection_info()
    print(f"📈 Final knowledge base stats: {final_stats}")

if __name__ == "__main__":
    initialize_knowledge_base()
