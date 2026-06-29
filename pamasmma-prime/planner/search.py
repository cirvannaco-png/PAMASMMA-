from dataclasses import dataclass, field
import heapq
from typing import Any, Dict, List, Optional, Tuple


@dataclass(order=True)
class Node:
    priority: float
    state: Dict[str, Any] = field(compare=False)
    cost: float = field(compare=False)
    parent: Optional["Node"] = field(compare=False, default=None)
    action: Optional[Dict[str, Any]] = field(compare=False, default=None)


class AStarPlanner:
    """
    Pamasmma Prime A* Tree-Search Planner

    Performs multi-step reasoning using heuristic search over action space.
    This is the first true foresight engine in the system.
    """

    def __init__(self, objective_system=None, governance=None, heuristic=None):
        self.objective_system = objective_system
        self.governance = governance
        self.heuristic = heuristic or (lambda s, g: 0.0)

    def plan(self, start_state: Dict[str, Any], goal: Dict[str, Any], max_depth: int = 5) -> List[Dict[str, Any]]:
        open_set: List[Node] = []
        closed_set = set()

        root = Node(priority=0.0, state=start_state, cost=0.0)
        heapq.heappush(open_set, root)

        while open_set:
            current = heapq.heappop(open_set)

            state_key = self._hash_state(current.state)
            if state_key in closed_set:
                continue
            closed_set.add(state_key)

            if self._is_goal(current.state, goal):
                return self._reconstruct_path(current)

            if self._depth(current) >= max_depth:
                continue

            for action in self._expand_actions(current.state, goal):
                if self.governance:
                    decision = self.governance.evaluate(action)
                    if decision["status"] != "allowed":
                        continue

                new_state = self._transition(current.state, action)
                cost = current.cost + self._cost(action)

                heuristic_score = self.heuristic(new_state, goal)
                priority = cost + heuristic_score

                child = Node(
                    priority=priority,
                    state=new_state,
                    cost=cost,
                    parent=current,
                    action=action
                )

                heapq.heappush(open_set, child)

        return []

    def _expand_actions(self, state: Dict[str, Any], goal: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"type": "analyze", "payload": goal},
            {"type": "refine", "payload": goal},
            {"type": "execute", "payload": goal}
        ]

    def _transition(self, state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        new_state = dict(state)
        new_state["last_action"] = action
        return new_state

    def _cost(self, action: Dict[str, Any]) -> float:
        return 1.0

    def _is_goal(self, state: Dict[str, Any], goal: Dict[str, Any]) -> bool:
        return state.get("completed") == goal.get("target")

    def _hash_state(self, state: Dict[str, Any]) -> str:
        return str(sorted(state.items()))

    def _depth(self, node: Node) -> int:
        d = 0
        while node.parent:
            d += 1
            node = node.parent
        return d

    def _reconstruct_path(self, node: Node) -> List[Dict[str, Any]]:
        path = []
        while node.parent:
            path.append(node.action)
            node = node.parent
        return list(reversed(path))
