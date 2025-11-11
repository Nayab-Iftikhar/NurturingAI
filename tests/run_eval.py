"""
Script to run agent evaluation using DeepEval
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import json
from datetime import datetime
from apps.agent.langgraph_agent import get_agent
from services.document_processor import process_document
from leads.models import Lead
import tempfile


def create_test_data():
    """Create test data for evaluation"""
    # Create test leads
    Lead.objects.get_or_create(
        lead_id='EVAL_L1',
        defaults={
            'name': 'Evaluation Lead 1',
            'email': 'eval1@example.com',
            'country_code': '1',
            'phone': '1111111111',
            'project_name': 'Evaluation Project',
            'unit_type': '2 bed',
            'status': 'Connected',
            'last_conversation_summary': 'Interested in 2 bed units'
        }
    )
    
    # Create sample document content
    sample_text = """
    Property Brochure: Luxury Residences
    
    Facilities:
    - Olympic-size swimming pool
    - Fully equipped gymnasium
    - Children's playground
    - Rooftop garden
    - Covered parking
    
    Amenities:
    - Shopping mall within 500m
    - International schools nearby
    - Hospital within 2km
    - Public transport connectivity
    - 24/7 security
    
    Unit Types:
    - Studio apartments (500 sqft)
    - 1 Bedroom (750 sqft)
    - 2 Bedroom (1100 sqft)
    - 3 Bedroom (1500 sqft)
    """
    
    # Save to temp file and process
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
        tmp_file.write(sample_text)
        tmp_file_path = tmp_file.name
    
    try:
        process_document(
            file_path=tmp_file_path,
            project_name='Evaluation Project',
            uploaded_by='eval_user'
        )
    finally:
        os.unlink(tmp_file_path)


def run_evaluation():
    """Run DeepEval evaluation"""
    try:
        from deepeval import evaluate
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, ContextualRelevancyMetric
        from deepeval.test_case import LLMTestCase
    except ImportError:
        print("ERROR: DeepEval not installed. Install it with: pip install deepeval")
        sys.exit(1)
    
    # Create test data
    print("Creating test data...")
    create_test_data()
    
    # Initialize agent
    print("Initializing agent...")
    agent = get_agent()
    
    # Define test cases
    test_cases = [
        {
            'input': 'What are the facilities and amenities in this property?',
            'expected_output': 'The property has facilities like swimming pool, gym, playground, rooftop garden, and parking. Amenities include shopping mall, schools, hospital, public transport, and 24/7 security.',
            'context': 'Property brochure information',
            'expected_tool': 'document_rag'
        },
        {
            'input': 'How many leads are in the database?',
            'expected_output': 'A number indicating the count of leads in the database',
            'context': 'Database query',
            'expected_tool': 'text_to_sql'
        },
        {
            'input': 'What unit types are available?',
            'expected_output': 'Studio apartments, 1 Bedroom, 2 Bedroom, and 3 Bedroom units are available',
            'context': 'Property brochure information',
            'expected_tool': 'document_rag'
        },
        {
            'input': 'Show me all leads for Evaluation Project',
            'expected_output': 'A list of leads for Evaluation Project',
            'context': 'Database query',
            'expected_tool': 'text_to_sql'
        }
    ]
    
    print(f"Running evaluation on {len(test_cases)} test cases...")
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}/{len(test_cases)}: {test_case['input']}")
        
        # Get agent response
        agent_result = agent.query(
            query=test_case['input'],
            project_name='Evaluation Project'
        )
        
        actual_output = agent_result['response']
        tool_used = agent_result.get('tool_used', 'unknown')
        
        print(f"Tool used: {tool_used}")
        print(f"Response: {actual_output[:100]}...")
        
        # Create test case for DeepEval
        llm_test_case = LLMTestCase(
            input=test_case['input'],
            actual_output=actual_output,
            expected_output=test_case['expected_output'],
            context=test_case['context']
        )
        
        # Evaluate metrics
        metrics_results = {}
        
        try:
            relevancy_metric = AnswerRelevancyMetric(threshold=0.7)
            relevancy_result = relevancy_metric.measure(llm_test_case)
            metrics_results['relevancy'] = {
                'score': relevancy_result.score,
                'success': relevancy_result.success,
                'reason': relevancy_result.reason
            }
        except Exception as e:
            metrics_results['relevancy'] = {'error': str(e)}
        
        try:
            faithfulness_metric = FaithfulnessMetric(threshold=0.7)
            faithfulness_result = faithfulness_metric.measure(llm_test_case)
            metrics_results['faithfulness'] = {
                'score': faithfulness_result.score,
                'success': faithfulness_result.success,
                'reason': faithfulness_result.reason
            }
        except Exception as e:
            metrics_results['faithfulness'] = {'error': str(e)}
        
        try:
            contextual_metric = ContextualRelevancyMetric(threshold=0.7)
            contextual_result = contextual_metric.measure(llm_test_case)
            metrics_results['contextual_relevancy'] = {
                'score': contextual_result.score,
                'success': contextual_result.success,
                'reason': contextual_result.reason
            }
        except Exception as e:
            metrics_results['contextual_relevancy'] = {'error': str(e)}
        
        # Store results
        results.append({
            'test_case_number': i,
            'input': test_case['input'],
            'actual_output': actual_output,
            'expected_output': test_case['expected_output'],
            'expected_tool': test_case['expected_tool'],
            'actual_tool': tool_used,
            'tool_match': tool_used == test_case['expected_tool'],
            'metrics': metrics_results
        })
    
    # Calculate averages
    relevancy_scores = [r['metrics'].get('relevancy', {}).get('score', 0) 
                       for r in results if 'score' in r['metrics'].get('relevancy', {})]
    faithfulness_scores = [r['metrics'].get('faithfulness', {}).get('score', 0) 
                          for r in results if 'score' in r['metrics'].get('faithfulness', {})]
    contextual_scores = [r['metrics'].get('contextual_relevancy', {}).get('score', 0) 
                        for r in results if 'score' in r['metrics'].get('contextual_relevancy', {})]
    
    # Save results
    results_file = BASE_DIR / 'agent_evaluation_scores.json'
    evaluation_data = {
        'evaluation_date': datetime.now().isoformat(),
        'total_test_cases': len(test_cases),
        'summary': {
            'average_relevancy': sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0,
            'average_faithfulness': sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0,
            'average_contextual_relevancy': sum(contextual_scores) / len(contextual_scores) if contextual_scores else 0,
            'tool_accuracy': sum(1 for r in results if r['tool_match']) / len(results) if results else 0
        },
        'results': results
    }
    
    with open(results_file, 'w') as f:
        json.dump(evaluation_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print("EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"Results saved to: {results_file}")
    print(f"\nSummary:")
    print(f"  Average Relevancy: {evaluation_data['summary']['average_relevancy']:.2f}")
    print(f"  Average Faithfulness: {evaluation_data['summary']['average_faithfulness']:.2f}")
    print(f"  Average Contextual Relevancy: {evaluation_data['summary']['average_contextual_relevancy']:.2f}")
    print(f"  Tool Accuracy: {evaluation_data['summary']['tool_accuracy']:.2%}")
    print(f"{'='*60}")


if __name__ == '__main__':
    run_evaluation()

