#!/usr/bin/env python3
"""
Script to systematically fix API route tests by adding proper mocking
"""

import re

def fix_api_route_test(content):
    """Fix API route test by wrapping service calls with proper mocking"""
    
    # Pattern to find test functions
    test_pattern = r'(def test_api_v2_\w+\(client\):.*?)(?=\ndef test_|$)'
    
    def fix_test_function(match):
        test_func = match.group(1)
        
        # Skip already fixed tests (those that start with 'with patch')
        if 'with patch(' in test_func:
            return test_func
        
        lines = test_func.split('\n')
        
        # Find service calls that need mocking
        services_to_mock = []
        for line in lines:
            if 'get_stock_service()' in line:
                services_to_mock.append('stock_service')
            elif 'get_fmp_client()' in line:
                services_to_mock.append('fmp_client')
            elif 'get_auth_manager()' in line:
                services_to_mock.append('auth_manager')
            elif 'get_portfolio_manager()' in line:
                services_to_mock.append('portfolio_manager')
            elif 'get_undervaluation_analyzer()' in line:
                services_to_mock.append('undervaluation_analyzer')
        
        if not services_to_mock:
            return test_func
        
        # Extract function signature
        func_signature = lines[0]
        
        # Extract the body (everything after the function signature)
        body_lines = lines[1:]
        
        # Create mock setup
        mock_lines = []
        
        if 'stock_service' in services_to_mock:
            mock_lines.extend([
                "    with patch('api_routes.get_stock_service') as mock_get_service:",
                "        mock_stock_service = MagicMock()"
            ])
            
            # Replace service assignment lines
            for i, line in enumerate(body_lines):
                if line.strip().startswith('stock_service = get_stock_service()'):
                    body_lines[i] = '        mock_get_service.return_value = mock_stock_service'
                elif line.strip().startswith('stock_service.'):
                    # Replace with mock calls
                    body_lines[i] = line.replace('stock_service.', 'mock_stock_service.')
        
        # Add other service mocks if needed
        for service in services_to_mock:
            if service == 'fmp_client':
                mock_lines.append("        with patch('api_routes.get_fmp_client') as mock_get_fmp:")
                mock_lines.append("            mock_fmp_client = MagicMock()")
                mock_lines.append("            mock_get_fmp.return_value = mock_fmp_client")
            elif service == 'auth_manager':
                mock_lines.append("        with patch('api_routes.get_auth_manager') as mock_get_auth:")
                mock_lines.append("            mock_auth_manager = MagicMock()")
                mock_lines.append("            mock_get_auth.return_value = mock_auth_manager")
        
        # Indent body content properly
        indented_body = []
        for line in body_lines:
            if line.strip():  # Non-empty lines
                indented_body.append('        ' + line.lstrip())
            else:
                indented_body.append(line)
        
        # Combine everything
        fixed_test = func_signature + '\n' + '\n'.join(mock_lines) + '\n\n' + '\n'.join(indented_body)
        
        return fixed_test
    
    # Apply the fix to all test functions
    fixed_content = re.sub(test_pattern, fix_test_function, content, flags=re.DOTALL)
    
    return fixed_content

# Read the file
with open('/workspace/stockanalyst/tests/test_api_routes.py', 'r') as f:
    content = f.read()

# Fix the content
fixed_content = fix_api_route_test(content)

# Write back the fixed content
with open('/workspace/stockanalyst/tests/test_api_routes.py', 'w') as f:
    f.write(fixed_content)

print("Fixed API route tests")