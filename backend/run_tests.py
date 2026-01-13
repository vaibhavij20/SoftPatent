"""
Run all tests and generate a comprehensive report.
"""
import unittest
import sys
import os
import json
from datetime import datetime
from pathlib import Path

def run_tests():
    """Run all tests and return results."""
    # Discover and run all tests
    test_dir = str(Path(__file__).parent / 'tests')
    suite = unittest.TestLoader().discover(test_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, failfast=True)
    result = runner.run(unittest.TestSuite(suite))
    
    # Generate report
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'tests_run': result.testsRun,
        'failures': len(result.failures) if hasattr(result, 'failures') else 0,
        'errors': len(result.errors) if hasattr(result, 'errors') else 0,
        'skipped': len(getattr(result, 'skipped', [])),
        'successful': result.wasSuccessful() if hasattr(result, 'wasSuccessful') else False,
        'test_cases': []
    }
    
    # Add test case details
    if hasattr(result, 'failures') and hasattr(result, 'errors'):
        for test_case, _ in result.failures + result.errors:
            report['test_cases'].append({
                'name': str(test_case),
                'status': 'failed' if test_case in [f[0] for f in result.failures] else 'error',
                'error': str(getattr(test_case, '_testMethodName', 'unknown'))
            })
    
    # Save report
    report_path = Path('test_results')
    report_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = report_path / f'test_report_{timestamp}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to: {report_file.absolute()}")
    return report['successful']

if __name__ == "__main__":
    print("Running GNN Invariant Classifier Tests")
    print("=" * 40)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the test report.")
        sys.exit(1)
