import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/app/')))

from server import route_query

def test_route_query_simples():
    state = {"categoria": "simples"}
    proximo_no = route_query(state)
    assert proximo_no == "handle_technical"

def test_route_query_complexa():
    state = {"categoria": "complexa"}
    proximo_no = route_query(state)
    assert proximo_no == "handle_web_search"

def test_route_query_outro_valor():
    state = {"categoria": "desconhecida"}
    proximo_no = route_query(state)
    assert proximo_no == "handle_web_search"  # Assume 'handle_web_search' para valores não reconhecidos
