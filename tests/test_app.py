import pytest
from unittest.mock import patch, Mock
from app import app, determine_tool, get_insights

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200

@patch('app.OpenAI')
def test_query_polygon_news(mock_openai, client):
    mock_response = Mock()
    mock_response.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="[PolygonTickerNews, {'ticker': 'AAPL'}]"))]
    )
    mock_openai.return_value = mock_response

    response = client.post('/query', data={'input_text': "What is the latest news on AAPL?"})
    assert response.status_code == 200
    assert "output" in response.json

@patch('app.OpenAI')
def test_query_polygon_details(mock_openai, client):
    mock_response = Mock()
    mock_response.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="[PolygonTickerDetails, {'ticker': 'AAPL'}]"))]
    )
    mock_openai.return_value = mock_response

    response = client.post('/query', data={'input_text': "Tell me about Apple Inc."})
    assert response.status_code == 200
    assert "output" in response.json

@patch('app.OpenAI')
def test_query_polygon_aggregates(mock_openai, client):
    mock_response = Mock()
    mock_response.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="[PolygonAggregates, {'ticker': 'AAPL', 'timespan': 'day', 'timespan_multiplier': 1, 'from_date': '2024-03-07', 'to_date': '2024-03-14'}]"))]
    )
    mock_openai.return_value = mock_response

    response = client.post('/query', data={'input_text': "What has been Apple's daily closing price between March 7, 2024, and March 14, 2024?"})
    assert response.status_code == 200
    assert "output" in response.json

def test_get_insights_invalid_tool():
    invalid_tool_name = "InvalidToolName"
    api_output = ["Sample output"]
    question = "What is the latest news on AAPL?"
    result = get_insights(invalid_tool_name, api_output, question)
    assert result == "Invalid input. Please provide a valid tool name."

def test_determine_tool_parsing_error():
    malformed_output = "This is not a valid output"
    
    with patch('app.OpenAI') as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content=malformed_output))]
        mock_client.chat.completions.create.return_value = mock_completion

        with pytest.raises(IndexError) as exc_info:
            determine_tool("What is the latest news on AAPL?")
        
        assert "list index out of range" in str(exc_info.value)