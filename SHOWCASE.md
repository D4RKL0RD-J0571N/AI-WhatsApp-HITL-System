# Enterprise AI CRM: System Showcase.

This document serves as a visual guide to the internal architecture and data flows of the **Human-in-the-Loop AI Orchestrator**. 
These diagrams visualize how we handle high-concurrency messaging, deterministic guardrails, and real-time human approval.

## 1. High-Level Data Flow

This diagram illustrates the journey of a single message from WhatsApp entrance to the final AI response.

```mermaid
graph TD
    User([End User]) -->|1. Sends Message| API[FastAPI Gateway]
    
    subgraph "Trust & Safety Layer"
        API -->|2. Pre-Scan| Guard[Guardrail Engine]
        Guard -->|3a. Blocked| BlockedDB[(Security Log)]
        Guard -->|3b. Safe| Agent[AI Orchestrator]
    end
    
    subgraph "Intelligence Layer"
        Agent -->|4. Build Context| Context[Dynamic Prompt Builder]
        Context -->|5. Inference| LLM[Local LLM / OpenAI]
        LLM -->|6. JSON Response| Agent
    end
    
    subgraph "Verification Layer"
        Agent -->|7. Audit Check| Audit[Confidence Auditor]
        Audit -->|8a. High Confidence| AutoSend[Auto-Reply System]
        Audit -->|8b. Low Confidence| HITL[Human Review Queue]
    end
    
    HITL -->|9. WebSocket Push| Dashboard[Admin Dashboard]
    Dashboard -->|10. Approve/Edit| Finalizer[Response Finalizer]
    
    AutoSend -->|11. Send| WhatsApp[WhatsApp API]
    Finalizer -->|11. Send| WhatsApp
    WhatsApp -->|12. Deliver| User

    style Guard fill:#f56,stroke:#333,stroke-width:2px,color:white
    style LLM fill:#66f,stroke:#333,stroke-width:2px,color:white
    style HITL fill:#fa0,stroke:#333,stroke-width:2px,color:white
```

---

## 2. The Human-in-the-Loop (HITL) Protocol

A detailed sequence diagram showing the WebSocket negotiation when a message is flagged for manual review.

```mermaid
sequenceDiagram
    autonumber
    participant Client as WhatsApp User
    participant System as AI Backend
    participant DB as Database
    participant Admin as Human Admin (Dashboard)

    Client->>System: "I want a discount on bulk orders"
    
    rect rgb(240, 240, 240)
        Note right of System: AI Analysis
        System->>System: 1. Classify Intent: "Sales negotiation"
        System->>System: 2. Calculate Confidence: 65% (Low)
        System->>DB: Log "Pending Review" Event
    end
    
    System->>Admin: [WebSocket] PUSH_EVENT: {id: 123, status: "pending"}
    
    rect rgb(255, 230, 230)
        Note right of Admin: Manual Review
        Admin->>System: [WebSocket] GET_DETAILS: {id: 123}
        System-->>Admin: {text: "I want a discount...", suggested_reply: "Please contact sales..."}
        Admin->>Admin: Edits response to add specific pricing
        Admin->>System: [API] ACTION_APPROVE: {id: 123, final_text: "We offer 10% on >500 units."}
    end

    System->>DB: Update Status: "Approved"
    System-->>Client: "We offer 10% on >500 units."
    System->>Admin: [WebSocket] ACK: {id: 123, status: "sent"}
```

---

## 3. "Zero-Echo" Security Guardrail

How the system handles malicious or out-of-scope inputs **deterministically**, without even querying the LLM.

```mermaid
flowchart LR
    Input[Inbound Message] --> Tokenizer{Keyword Tokenizer}
    
    Tokenizer -->|Contains 'Politics'| Violation[Security Violation]
    Tokenizer -->|Contains 'Medical'| Violation
    Tokenizer -->|Clean| BusinessCheck{Business Logic Check}
    
    BusinessCheck -->|Topic: 'Support'| Allowed[Pass to LLM]
    BusinessCheck -->|Topic: 'Competitor'| OutOfScope[Out of Scope]
    
    Violation -->|Action| BanLog[Log & Ban IP]
    Violation -->|Response| Silence[No Reply / Generic 400]
    
    OutOfScope -->|Response| SoftRefusal["I cannot discuss that topic."]
    
    style Violation fill:#bd2c00,stroke:#333,stroke-width:2px,color:white
    style Allowed fill:#2cbe4e,stroke:#333,stroke-width:2px,color:white
```

---

## 4. Database Schema (Entities)

The core data models ensuring auditability and traceability.

```mermaid
erDiagram
    CLIENT ||--o{ CONVERSATION : initiates
    CONVERSATION ||--|{ MESSAGE : contains
    
    MESSAGE {
        uuid id
        string content
        string sender_role
        string status
        float confidence_score
        timestamp created_at
    }

    MESSAGE ||--o| SECURITY_AUDIT : generates
    
    SECURITY_AUDIT {
        int id
        string classification
        string triggered_keywords
        int latency_ms
        int tokens_used
    }

    AI_CONFIG ||--|{ SNAPSHOT : versions
    
    AI_CONFIG {
        string business_name
        json rules
        float auto_respond_threshold
        string primary_color
    }
```
