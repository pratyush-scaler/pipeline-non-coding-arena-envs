"""Verify any optimal path in a public finite acyclic graph.

Primary objective: maximize the minimum node/edge capacity on the whole path.
Secondary objective: minimize the sum of node/edge costs among primary optima.
No path is preferred when the two objective values tie. This module executes no
source program and accepts no Python expressions.
"""
from collections import deque
from decimal import Decimal, localcontext
from fractions import Fraction
import re


class InvalidProblem(ValueError):
    """Invalid source data; must be a grader fault, never a model failure."""


def _reported(number, schema=None):
    if isinstance(schema, dict) and schema.get('type') == 'string':
        with localcontext() as context:
            context.prec = 160
            return format(Decimal(number.numerator) / Decimal(number.denominator), 'f')
    return int(number) if number.denominator == 1 else float(number)


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}', value.strip()):
        raise InvalidProblem('node identifiers must be nonempty ASCII identifiers')
    return value.strip().casefold()


def _number(value, maximum=10**12):
    if type(value) not in (str, int, float) or len(str(value)) > 80:
        raise InvalidProblem('capacity and cost must be finite decimal numbers')
    text = str(value).strip()
    if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,3})?', text):
        raise InvalidProblem('capacity and cost must be finite decimal numbers')
    number = Fraction(text)
    if number < 0 or number > maximum or number.denominator > 10**12:
        raise InvalidProblem('number exceeds the declared nonnegative decimal bounds')
    return number


def prepare(problem):
    """Validate all source data before looking at a submitted witness."""
    if not isinstance(problem, dict) or set(problem) != {'nodes', 'edges', 'start', 'end'}:
        raise InvalidProblem('path problem requires nodes, edges, start and end')
    rows, links = problem['nodes'], problem['edges']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
        raise InvalidProblem('path problem requires 1..256 nodes')
    if not isinstance(links, list) or len(links) > 16384:
        raise InvalidProblem('path problem permits at most 16384 edges')
    nodes, edges = {}, {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', 'capacity', 'cost'}:
            raise InvalidProblem('each node requires id, capacity and cost')
        key = _id(row['id'])
        if key in nodes:
            raise InvalidProblem('duplicate node identifier')
        nodes[key] = (_number(row['capacity']), _number(row['cost']))
    start, end = _id(problem['start']), _id(problem['end'])
    if start not in nodes or end not in nodes:
        raise InvalidProblem('start and end must name declared nodes')
    adjacent, indegree = {key: [] for key in nodes}, {key: 0 for key in nodes}
    for row in links:
        if not isinstance(row, dict) or set(row) != {'from', 'to', 'capacity', 'cost'}:
            raise InvalidProblem('each edge requires from, to, capacity and cost')
        src, dst = _id(row['from']), _id(row['to'])
        if src not in nodes or dst not in nodes:
            raise InvalidProblem('edge endpoint is not a declared node')
        if (src, dst) in edges:
            raise InvalidProblem('parallel edges require distinct intermediate nodes')
        edges[src, dst] = (_number(row['capacity']), _number(row['cost']))
        adjacent[src].append(dst)
        indegree[dst] += 1
    ready, order = deque(key for key in nodes if not indegree[key]), []
    while ready:
        src = ready.popleft()
        order.append(src)
        for dst in adjacent[src]:
            indegree[dst] -= 1
            if not indegree[dst]:
                ready.append(dst)
    if len(order) != len(nodes):
        raise InvalidProblem('path problem must be acyclic, including disconnected components')

    # First solve only the primary problem. Selecting one locally best
    # lexicographic prefix is unsound: a later bottleneck can erase its advantage.
    widest = {start: nodes[start][0]}
    for src in order:
        if src not in widest:
            continue
        for dst in adjacent[src]:
            candidate = min(widest[src], edges[src, dst][0], nodes[dst][0])
            if dst not in widest or candidate > widest[dst]:
                widest[dst] = candidate
    if end not in widest:
        optimum = None
    else:
        threshold = widest[end]
        # Restrict the graph to the optimal capacity threshold, then solve the
        # ordinary shortest-path problem there. Every tied optimum stays valid.
        shortest = {start: nodes[start][1]}
        for src in order:
            if src not in shortest:
                continue
            for dst in adjacent[src]:
                edge_capacity, edge_cost = edges[src, dst]
                if edge_capacity < threshold or nodes[dst][0] < threshold:
                    continue
                candidate = shortest[src] + edge_cost + nodes[dst][1]
                if dst not in shortest or candidate < shortest[dst]:
                    shortest[dst] = candidate
        optimum = (threshold, shortest[end])
    return {'nodes': nodes, 'edges': edges, 'start': start, 'end': end, 'optimum': optimum,
            'order': order, 'adjacent': adjacent, 'shortest': shortest if optimum else {}}


def reference_witness(prepared, schema=None):
    """Compute one valid optimum from source, never from a stored submission."""
    if prepared['optimum'] is None:
        return {'feasible': False, 'path': []}
    capacity, cost = prepared['optimum']
    current = prepared['end']
    path = [current]
    while current != prepared['start']:
        choices = sorted(src for (src, dst), (edge_capacity, edge_cost) in prepared['edges'].items()
                         if dst == current and src in prepared['shortest'] and edge_capacity >= capacity
                         and prepared['shortest'][src] + edge_cost + prepared['nodes'][current][1] == prepared['shortest'][current])
        current = choices[0]
        path.append(current)
    properties = schema.get('properties', {}) if isinstance(schema, dict) else {}
    return {'feasible': True, 'path': list(reversed(path)),
            'bottleneck': _reported(capacity, properties.get('bottleneck')),
            'cost': _reported(cost, properties.get('cost'))}


def decision_signature(prepared):
    """Identify the full accepted path set, without enumerating its members.

Used by source-dependency probes: changing an unused node is not a changed
professional answer. A change to a tied optimal route still matters even when
the optimum's two numbers remain unchanged.
"""
    optimum = prepared['optimum']
    if optimum is None:
        return {'feasible': False}
    capacity, total = optimum
    suffix = {prepared['end']: Fraction(0)}
    for src in reversed(prepared['order']):
        if src == prepared['end'] or prepared['nodes'][src][0] < capacity:
            continue
        choices = [cost + prepared['nodes'][dst][1] + suffix[dst]
                   for dst in prepared['adjacent'][src]
                   for edge_capacity, cost in [prepared['edges'][src, dst]]
                   if edge_capacity >= capacity and dst in suffix]
        if choices:
            suffix[src] = min(choices)
    optimal_edges = []
    for (src, dst), (edge_capacity, cost) in prepared['edges'].items():
        if (src in prepared['shortest'] and dst in suffix and edge_capacity >= capacity
                and prepared['nodes'][dst][0] >= capacity
                and prepared['shortest'][src] + cost + prepared['nodes'][dst][1] + suffix[dst] == total):
            optimal_edges.append([src, dst])
    return {'feasible': True, 'start': prepared['start'], 'end': prepared['end'],
            'bottleneck': str(capacity), 'cost': str(total), 'edges': sorted(optimal_edges)}


def check_witness(prepared, answer, tolerance=0):
    """Return failure for bad submissions; source errors are raised by prepare."""
    tolerance = _number(tolerance)
    required = {'feasible', 'path', 'bottleneck', 'cost'}
    if not isinstance(answer, dict) or type(answer.get('feasible')) is not bool:
        return False, 'answer requires a feasible boolean'
    if prepared['optimum'] is None:
        passed = (set(answer) == {'feasible', 'path'}
                  and answer['feasible'] is False and answer['path'] == [])
        return passed, '' if passed else 'no start-to-end path exists'
    if set(answer) != required:
        return False, 'a feasible answer requires path, bottleneck and cost'
    path = answer['path']
    if answer['feasible'] is not True or not isinstance(path, list) or not 1 <= len(path) <= len(prepared['nodes']):
        return False, 'a complete feasible path is required'
    try:
        path = [_id(item) for item in path]
        claimed = (_number(answer['bottleneck']),
                   _number(answer['cost'], (2 * len(prepared['nodes']) - 1) * 10**12))
    except InvalidProblem:
        return False, 'invalid path identifier or reported metric'
    if path[0] != prepared['start'] or path[-1] != prepared['end'] or len(set(path)) != len(path):
        return False, 'path must connect the declared endpoints without repetition'
    if any(node not in prepared['nodes'] for node in path):
        return False, 'path names an undeclared node'
    links = list(zip(path, path[1:]))
    if any(link not in prepared['edges'] for link in links):
        return False, 'path uses an unavailable transition'
    values = [prepared['nodes'][node] for node in path] + [prepared['edges'][link] for link in links]
    measured = (min(capacity for capacity, _ in values), sum(cost for _, cost in values))
    if measured != prepared['optimum']:
        return False, 'path is not globally optimal under the two public objectives'
    if any(abs(a - b) > tolerance for a, b in zip(claimed, measured)):
        return False, 'reported metrics do not describe the submitted path'
    return True, ''
