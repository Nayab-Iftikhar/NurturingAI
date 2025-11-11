import logging
from typing import Dict, Any, Optional
from django.db import connection
from services.vanna_service import get_vanna_service
import re
from services.llm_utils import get_llm_candidates

logger = logging.getLogger(__name__)


class TextToSQLTool:
    """Tool for converting natural language queries to SQL using Vanna"""
    
    def __init__(self):
        self.vanna_service = get_vanna_service()
        self._ensure_training_data()
    
    def _ensure_training_data(self):
        """Ensure training data exists in ChromaDB"""
        # Check if collection has data
        try:
            results = self.vanna_service.vanna_collection.get(limit=1)
            if not results.get('ids') or len(results['ids']) == 0:
                self._seed_training_data()
        except Exception:
            # Collection might not exist or be empty, seed it
            self._seed_training_data()
    
    def _seed_training_data(self):
        """Seed initial training data for Vanna"""
        from leads.models import Lead
        from campaigns.models import Campaign, CampaignLead
        
        training_data = []
        
        # Add DDL for leads table
        leads_ddl = """
        CREATE TABLE leads (
            id INTEGER PRIMARY KEY,
            lead_id VARCHAR(20) UNIQUE,
            name VARCHAR(255),
            email VARCHAR(255),
            country_code VARCHAR(5),
            phone VARCHAR(32),
            project_name VARCHAR(255),
            unit_type VARCHAR(255),
            budget_min DECIMAL(12,2),
            budget_max DECIMAL(12,2),
            status VARCHAR(64),
            last_conversation_date DATE,
            last_conversation_summary TEXT,
            created_at DATETIME,
            updated_at DATETIME
        );
        """
        
        # Add DDL for campaigns table
        campaigns_ddl = """
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            project_name VARCHAR(255),
            channel VARCHAR(20),
            offer_details TEXT,
            created_by_id INTEGER,
            created_at DATETIME,
            updated_at DATETIME,
            is_active BOOLEAN
        );
        """
        
        # Add DDL for campaign_leads table
        campaign_leads_ddl = """
        CREATE TABLE campaign_leads (
            id INTEGER PRIMARY KEY,
            campaign_id INTEGER,
            lead_id INTEGER,
            message_sent BOOLEAN,
            message_sent_at DATETIME,
            created_at DATETIME
        );
        """
        
        # Add documentation
        documentation = [
            "The leads table contains information about potential customers including their contact details, budget, preferred unit type, and project interests.",
            "The campaigns table stores marketing campaigns with project names, channels (email or whatsapp), and offer details.",
            "The campaign_leads table links leads to campaigns, tracking which leads are part of which campaign.",
            "budget_min and budget_max represent the lead's budget range in the base currency.",
            "status field in leads can be: Not Connected, Connected, Visit scheduled, Visit done not purchased, Purchased, Not interested.",
            "channel in campaigns can be 'email' or 'whatsapp'.",
        ]
        
        # Add SQL examples
        sql_examples = [
            "SELECT COUNT(*) FROM leads WHERE status = 'Connected';",
            "SELECT project_name, COUNT(*) as count FROM leads GROUP BY project_name;",
            "SELECT * FROM leads WHERE budget_min >= 1000000 AND budget_max <= 5000000;",
            "SELECT l.* FROM leads l JOIN campaign_leads cl ON l.id = cl.lead_id WHERE cl.campaign_id = 1;",
            "SELECT unit_type, COUNT(*) FROM leads GROUP BY unit_type;",
            "SELECT * FROM campaigns WHERE is_active = 1;",
        ]
        
        # Prepare training data
        all_docs = [leads_ddl, campaigns_ddl, campaign_leads_ddl] + documentation + sql_examples
        metadatas = []
        ids = []
        
        for i, doc in enumerate(all_docs):
            metadata = {"type": "ddl" if i < 3 else ("documentation" if i < 9 else "sql_example")}
            metadatas.append(metadata)
            ids.append(f"training_{i}")
        
        # Add to ChromaDB
        self.vanna_service.add_training_data(
            documents=all_docs,
            metadatas=metadatas,
            ids=ids
        )
    
    def execute(self, query: str, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a natural language query using Text-to-SQL
        
        Args:
            query: Natural language query
            project_name: Optional project name for context
            
        Returns:
            Dict with 'sql', 'result', and 'response' keys
        """
        try:
            # Get similar training data
            training_results = self.vanna_service.get_similar_training_data(query, n_results=5)
            
            # Build context from training data
            context = "\n".join(training_results.get('documents', [])[0] if training_results.get('documents') else [])
            
            prompt = f"""Given the following database schema and examples:

{context}

Convert this natural language query to SQL: "{query}"

Rules:
- Only generate SELECT queries
- Use proper SQLite syntax
- Return only the SQL query, no explanations
- If the query mentions a project name, use the project_name column
- Be precise with table and column names

SQL Query:"""

            llm_candidates = get_llm_candidates(temperature=0)
            errors = []

            for provider, llm in llm_candidates:
                try:
                    response = llm.invoke(prompt)
                    sql_query = getattr(response, "content", str(response)).strip()

                    # Clean SQL (remove markdown code blocks if present)
                    sql_query = re.sub(r"```sql\n?", "", sql_query)
                    sql_query = re.sub(r"```\n?", "", sql_query)
                    sql_query = sql_query.strip()

                    # Execute SQL
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query)
                        columns = [col[0] for col in cursor.description] if cursor.description else []
                        rows = cursor.fetchall()

                        # Convert to list of dicts
                        result = [dict(zip(columns, row)) for row in rows] if columns else []

                    # Generate natural language response
                    result_summary = f"Found {len(result)} result(s)."
                    if result:
                        result_summary += f" Sample: {str(result[0])[:100]}"

                    response_prompt = f"""The user asked: "{query}"

SQL executed: {sql_query}

Results: {result_summary}

Provide a natural language answer based on the SQL results. Be concise and helpful."""

                    response_llm = llm.invoke(response_prompt)
                    natural_response = getattr(response_llm, "content", str(response_llm)).strip()

                    return {
                        "sql": sql_query,
                        "result": result,
                        "response": natural_response,
                        "tool": "text_to_sql",
                        "provider": provider,
                    }
                except Exception as exc:  # pragma: no cover - fallback path
                    logger.warning("TextToSQL provider %s failed: %s", provider, exc)
                    errors.append(f"{provider}: {exc}")
                    continue

            logger.error("All LLM providers failed for Text-to-SQL: %s", "; ".join(errors))
            return {
                "error": "All LLM providers failed to generate SQL.",
                "details": errors,
                "tool": "text_to_sql",
            }

        except Exception as e:
            return {
                "error": str(e),
                "tool": "text_to_sql"
            }

