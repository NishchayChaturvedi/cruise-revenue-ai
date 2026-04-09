# Cruise Revenue AI 🚢

An end-to-end agentic AI revenue intelligence system for the cruise industry, 
built on Norwegian Cruise Line Holdings (NCLH) data architecture.

## What It Does

A revenue analyst can:
- Ask questions in plain English against live cruise booking data
- Get AI-synthesized answers backed by specific numbers
- Trigger autonomous agents that detect revenue anomalies
- Review AI-generated pricing recommendations
- Approve or reject actions with a full audit log

## Demo

**Revenue Q&A:**
> "Which region has the highest cancellation rate?"
> → "Americas has the highest cancellation rate at 13.45% for Oceania brand..."

**Anomaly Detection:**
> Agent detects Regent Caribbean Classic at 68% occupancy with 31.82% cancellation rate
> → Recommends 25-30% price reduction with expected occupancy recovery to 85-90%

## Architecture

Synthetic Data (Python/Faker)
↓
Snowflake RAW Schema (Fivetran-style ingestion)
↓
dbt Transformations (Staging → Marts)
↓
┌───────────────────────────────┐
│         Gold Layer            │
│  MART_REVENUE                 │
│  MART_OCCUPANCY               │
│  MART_GUEST_LTV               │
│  MART_PRICING_SUMMARY         │
└───────────────────────────────┘
↓                    ↓
ML Models (MLflow)      RAG Pipeline

Cancellation Risk     - ChromaDB Vector Store
Revenue Forecast      - 5,200 Documents
Upsell Propensity     - Claude API
↓                    ↓
LangGraph Multi-Agent System

Anomaly Detector
Pricing Advisor
Escalation Agent (HITL)
↓
Streamlit Web App


## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Ingestion | Fivetran (simulated) + Python |
| Data Warehouse | Snowflake |
| Transformations | dbt Core |
| ML Models | scikit-learn + MLflow |
| Vector Store | ChromaDB |
| LLM | Anthropic Claude (claude-sonnet-4-5) |
| Agents | LangGraph |
| App | Streamlit |
| Orchestration | Prefect |
| Version Control | GitHub |

## Dataset

Synthetic dataset modeled after real cruise reservation systems:
- 50,000 booking records across 3 brands (Norwegian, Oceania, Regent)
- 18,297 guest profiles
- 43,982 onboard spend records
- 25,080 pricing log entries
- 8 itineraries across Caribbean, Alaska, Mediterranean, Europe, Americas, Bermuda, Hawaii, Asia

## ML Model Performance

| Model | Metric | Score |
|-------|--------|-------|
| Cancellation Risk | AUC-ROC | 0.83 |
| Revenue per Night | R² | 0.99 |
| Upsell Propensity | AUC-ROC | 0.82 |

## Project Structure

cruise-revenue-ai/
├── data/
│   ├── generate_data.py        # Synthetic dataset generator
│   └── load_to_snowflake.py    # Snowflake loader
├── dbt_project/
│   ├── models/
│   │   ├── staging/            # 4 staging views
│   │   └── marts/              # 4 gold tables
│   └── macros/                 # Custom schema macro
├── ml_models/
│   ├── features/               # Feature engineering
│   └── train.py                # Model training + MLflow
├── rag_pipeline/
│   ├── generate_summaries.py   # Snowflake → documents
│   ├── build_vectorstore.py    # ChromaDB indexing
│   └── rag_assistant.py        # RAG query engine
├── agents/
│   └── revenue_agents.py       # LangGraph agent pipeline
└── app/
└── main.py                 # Streamlit web app

## Setup

### Prerequisites
- Python 3.11
- Snowflake account
- Anthropic API key

### Installation
```bash
git clone https://github.com/NishchayChaturvedi/cruise-revenue-ai.git
cd cruise-revenue-ai
python3.11 -m venv venv
source venv/bin/activate
pip install snowflake-connector-python dbt-snowflake langchain \
    langchain-anthropic chromadb streamlit mlflow pandas \
    faker prefect cryptography python-dotenv langgraph langchain-core
```

### Configuration

Create `.env` file:

SNOWFLAKE_USER=your_user
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/snowflake_key.pem
ANTHROPIC_API_KEY=sk-ant-...

### Run
```bash
# 1. Generate synthetic data
python data/generate_data.py

# 2. Load to Snowflake
python data/load_to_snowflake.py

# 3. Run dbt transformations
cd dbt_project && dbt run && dbt test

# 4. Train ML models
cd .. && python -m ml_models.train

# 5. Build RAG vector store
python rag_pipeline/build_vectorstore.py

# 6. Launch app
streamlit run app/main.py
```

## Author

**Nishchay Chaturvedi**  
Senior Manager, Data Analytics & Insights  
[LinkedIn](https://linkedin.com/in/your-profile)  
[GitHub](https://github.com/NishchayChaturvedi)

---
*Built in one week as a learning project to explore the full AI/ML stack — 
from data engineering to agentic AI systems.*