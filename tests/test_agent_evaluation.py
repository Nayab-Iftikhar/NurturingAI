"""
DeepEval evaluation tests for the LangGraph agent
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from apps.agent.langgraph_agent import get_agent
from leads.models import Lead
from campaigns.models import Campaign, CampaignLead
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def evaluation_results_file():
    """Path to evaluation results file"""
    return Path(__file__).parent.parent / 'agent_evaluation_scores.json'


@pytest.mark.django_db
@pytest.mark.skipif(
    not os.getenv('OPENAI_API_KEY') and not os.getenv('OLLAMA_BASE_URL'),
    reason="No LLM API key or Ollama available for evaluation"
)
class TestAgentEvaluation:
    """Test agent evaluation using DeepEval"""
    
    def setup_method(self):
        """Setup method called before each test method"""
        self.test_lead = None
        self.test_campaign = None
        self.test_campaign_lead = None
        self.temp_files = []
        self.agent = None
    
    def teardown_method(self):
        """Teardown method called after each test method"""
        # Clean up test data
        if self.test_campaign_lead:
            try:
                self.test_campaign_lead.delete()
            except Exception:
                pass
        if self.test_campaign:
            try:
                self.test_campaign.delete()
            except Exception:
                pass
        if self.test_lead:
            try:
                self.test_lead.delete()
            except Exception:
                pass
        # Clean up temp files
        for tmp_file in self.temp_files:
            try:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            except (OSError, IOError):
                pass
        self.temp_files = []
    
    def test_agent_routing_document_rag(self, sample_pdf_file, temp_chromadb_dir):
        """Test agent routing to Document RAG for brochure queries"""
        # Setup: Process a document
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            sample_pdf_file.seek(0)
            tmp_file.write(sample_pdf_file.read())
            tmp_file_path = tmp_file.name
            self.temp_files.append(tmp_file_path)
        
        from services.document_processor import process_document
        process_document(
            file_path=tmp_file_path,
            project_name='Evaluation Project',
            uploaded_by='testuser'
        )
        
        # Test agent query
        self.agent = get_agent()
        result = self.agent.query(
            query="What are the facilities and amenities in this property?",
            project_name='Evaluation Project'
        )
        
        assert 'response' in result
        assert 'tool_used' in result
        # Should use document_rag for property-related queries
        assert result['tool_used'] == 'document_rag'
        assert len(result['response']) > 0
    
    def test_agent_routing_text_to_sql(self):
        """Test agent routing to Text-to-SQL for data queries"""
        # Setup: Create test leads
        self.test_lead = Lead.objects.create(
            lead_id='EVAL_SQL1',
            name='Eval Lead 1',
            email='eval1@example.com',
            country_code='1',
            phone='1111111111',
            project_name='Eval Project',
            unit_type='2 bed',
            status='Connected'
        )
        
        # Test agent query
        self.agent = get_agent()
        result = self.agent.query(
            query="How many leads are there?",
            project_name='Eval Project'
        )
        
        assert 'response' in result
        assert 'tool_used' in result
        # Should use text_to_sql for data queries
        assert result['tool_used'] == 'text_to_sql'
        assert len(result['response']) > 0
    
    def test_full_evaluation_suite(self, evaluation_results_file, sample_pdf_file, temp_chromadb_dir):
        """Run full evaluation suite and save results"""
        try:
            from deepeval import evaluate
            from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
            from deepeval.test_case import LLMTestCase
        except ImportError:
            pytest.skip("DeepEval not installed")
        
        # Setup test data
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            sample_pdf_file.seek(0)
            tmp_file.write(sample_pdf_file.read())
            tmp_file_path = tmp_file.name
            self.temp_files.append(tmp_file_path)
        
        from services.document_processor import process_document
        process_document(
            file_path=tmp_file_path,
            project_name='Full Eval Project',
            uploaded_by='testuser'
        )
        
        # Create test cases
        test_cases = [
            LLMTestCase(
                input="What are the facilities and amenities in this property?",
                actual_output="",  # Will be filled by agent
                expected_output="The property has facilities like swimming pool, gym, and parking. Amenities include shopping mall and schools nearby.",
                context="Property brochure information"
            ),
            LLMTestCase(
                input="How many leads are in the database?",
                actual_output="",  # Will be filled by agent
                expected_output="A number indicating the count of leads",
                context="Database query"
            )
        ]
        
        # Run agent and evaluate
        self.agent = get_agent()
        results = []
        
        for test_case in test_cases:
            # Get agent response
            agent_result = self.agent.query(
                query=test_case.input,
                project_name='Full Eval Project'
            )
            test_case.actual_output = agent_result['response']
            
            # Evaluate
            relevancy_metric = AnswerRelevancyMetric(threshold=0.7)
            faithfulness_metric = FaithfulnessMetric(threshold=0.7)
            
            relevancy_score = relevancy_metric.measure(test_case)
            faithfulness_score = faithfulness_metric.measure(test_case)
            
            results.append({
                'input': test_case.input,
                'actual_output': test_case.actual_output,
                'expected_output': test_case.expected_output,
                'tool_used': agent_result.get('tool_used', 'unknown'),
                'relevancy_score': relevancy_score.score,
                'faithfulness_score': faithfulness_score.score,
                'relevancy_success': relevancy_score.success,
                'faithfulness_success': faithfulness_score.success
            })
        
        # Save results
        evaluation_results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(evaluation_results_file, 'w') as f:
            json.dump({
                'evaluation_date': str(pytest.datetime.now()) if hasattr(pytest, 'datetime') else 'N/A',
                'total_test_cases': len(test_cases),
                'results': results,
                'average_relevancy': sum(r['relevancy_score'] for r in results) / len(results) if results else 0,
                'average_faithfulness': sum(r['faithfulness_score'] for r in results) / len(results) if results else 0
            }, f, indent=2)
        
        assert evaluation_results_file.exists()
