"""
This module provides a TaskPlanner to generate a JSON file with task dependencies
based on a natural language request.
"""
from pathlib import Path
import uuid
from typing import Dict, List, Any, Optional

from src.utils import config, load_json, print_run_config, print_run_summary, write_json
from src.utils.llm import config as llm_config


DEFAULT_LLM_SCENARIOS = {
    "create_meta": "code",
    "complete_code": "code",
    "verify_code": "code",
    "verify_error": "judge",
}


class TaskPlanner:
    """
    Generates a structured task plan (JSON) from a high-level description.
    """
    def __init__(
        self,
        tasks_dir: Path,
        output_root: Path | None = None,
        model: str | None = None,
        llm_scenarios: Optional[Dict[str, str]] = None,
        generation_run_id: str | None = None,
        max_generation_attempts: int = 3,
        use_rag: bool = True,
        property_catalog: Path | None = None,
        required_contracts: Dict[str, Any] | None = None,
    ):
        """Initialize the TaskPlanner."""
        self.tasks_dir = tasks_dir.resolve()
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.output_root = output_root.resolve() if output_root is not None else None
        self.model = model
        self.generation_run_id = generation_run_id or "unversioned"
        self.use_rag = use_rag
        self.property_catalog = (
            property_catalog.resolve()
            if property_catalog is not None
            else None
        )
        self.required_contracts = required_contracts or {}
        if max_generation_attempts <= 0:
            raise ValueError("max_generation_attempts must be positive")
        self.max_generation_attempts = max_generation_attempts
        self.llm_scenarios = {
            **DEFAULT_LLM_SCENARIOS,
            **(llm_scenarios or {}),
        }
        unknown = {
            scenario
            for scenario in self.llm_scenarios.values()
            if scenario not in llm_config.LLM_CONFIGS
        }
        if unknown:
            available = ", ".join(sorted(llm_config.LLM_CONFIGS))
            raise KeyError(
                f"Unknown LLM scenarios: {sorted(unknown)}. Available: {available}"
            )

    def _llm_params(self, task_name: str) -> Dict[str, str]:
        """Return the LLM params."""
        params = {
            "model_scenario": self.llm_scenarios[task_name],
        }
        if task_name == "verify_code":
            params["judge_model_scenario"] = self.llm_scenarios["verify_error"]
        if self.model:
            params["model"] = self.model
        params["generation_run_id"] = self.generation_run_id
        return params

    def _task_id(self, class_name: str, task_name: str) -> str:
        """Return the task ID."""
        identity = "|".join(
            (
                "dcb-v2-model-creation",
                self.generation_run_id,
                class_name,
                task_name,
            )
        )
        return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))

    def _required_contract_params(self, class_name: str) -> Dict[str, Any]:
        """Return the required contract params."""
        required = self.required_contracts.get(class_name)
        return (
            {"required_contract": required}
            if isinstance(required, dict) and required
            else {}
        )

    def create_task_plan(self, type_list_path: Path) -> Path:
        """
        Creates a JSON file with a plan for all the tasks based on a type list file.
        """
        type_list = load_json(type_list_path)

        all_tasks: Dict[str, Any] = {}
        for base_model_name, model_info in type_list.items():
            domain = model_info.get("domain", "Home")
            base_model_description = model_info.get("description")
            inherited_models = model_info.get("inherited_list", [])
            inherited_model_names = [item['class'] for item in inherited_models]
            inherited_model_descriptions = [item.get('description') for item in inherited_models]

            tasks = self._generate_tasks_for_model(
                base_model_name,
                domain,
                base_model_description,
                inherited_model_names,
                inherited_model_descriptions
            )
            all_tasks.update(tasks)

        plan_file = self.tasks_dir / "plans.json"
        write_json(plan_file, all_tasks)
        
        return plan_file

    def _generate_tasks_for_model(self, base_model_name: str,
                         domain: str = 'Home',
                         base_model_description: Optional[str] = None,
                         inherited_model_names: Optional[List[str]] = None,
                         inherited_model_descriptions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generates tasks for a single base model and its inherited models.
        """
        tasks: Dict[str, Any] = {}
        batch_id = (
            self.generation_run_id
            if self.generation_run_id != "unversioned"
            else "default"
        )
        project_path = self.output_root or (
            config.DEVICES_DIR / f"{domain}-{batch_id}"
        )
        use_rag = self.use_rag
        property_catalog = (
            str(self.property_catalog)
            if self.property_catalog is not None
            else None
        )

        # Base model tasks
        base_json_task_id = self._task_id(base_model_name, "create_meta")
        tasks[base_json_task_id] = {
            "task_id": base_json_task_id,
            "name": "create_meta",
            "params": {
                "name": base_model_name,
                "domain": domain,
                "desc": base_model_description,
                "base_json": "",
                "output": str(project_path / domain / base_model_name / f"{base_model_name}.json"),
                "use_rag": use_rag,
                "property_catalog": property_catalog,
                **self._required_contract_params(base_model_name),
                **self._llm_params("create_meta"),
            },
            "dependencies": [],
            "max_retries": self.max_generation_attempts,
        }

        base_template_task_id = self._task_id(base_model_name, "create_template")
        tasks[base_template_task_id] = {
            "task_id": base_template_task_id,
            "name": "create_template",
            "params": {
                "name": base_model_name,
                "json": str(project_path / domain / base_model_name / f"{base_model_name}.json"),
                "output": str(project_path / domain / base_model_name / f"{base_model_name}.template.py")
            },
            "dependencies": [base_json_task_id],
            "max_retries": 1,
        }

        base_py_task_id = self._task_id(base_model_name, "complete_code")
        tasks[base_py_task_id] = {
            "task_id": base_py_task_id,
            "name": "complete_code",
            "params": {
                "template": str(project_path / domain / base_model_name / f"{base_model_name}.template.py"),
                "output": str(project_path / domain / base_model_name / f"{base_model_name}.py"),
                "name": base_model_name,
                "domain": domain,
                "desc": base_model_description,
                "use_rag": use_rag,
                "property_catalog": property_catalog,
                **self._llm_params("complete_code"),
            },
            "dependencies": [base_template_task_id],
            "max_retries": self.max_generation_attempts,
        }

        base_verify_task_id = self._task_id(base_model_name, "verify_code")
        tasks[base_verify_task_id] = {
            "task_id": base_verify_task_id,
            "name": "verify_code",
            "params": {
                "name": base_model_name,
                "py": str(project_path / domain / base_model_name / f"{base_model_name}.py"),
                "output": str(project_path / domain / base_model_name / f"{base_model_name}_test.py"),
                "use_rag": use_rag,
                "domain": domain,
                "specification": str(
                    project_path
                    / domain
                    / base_model_name
                    / f"{base_model_name}.json"
                ),
                "property_catalog": property_catalog,
                "candidate_root": str(project_path / domain),
                **self._llm_params("verify_code"),
            },
            "dependencies": [base_py_task_id],
            "max_retries": self.max_generation_attempts,
        }

        # Inherited model tasks
        if inherited_model_names:
            for i, model_name in enumerate(inherited_model_names):
                desc = inherited_model_descriptions[i] if inherited_model_descriptions and i < len(inherited_model_descriptions) else ""
                
                inherited_json_task_id = self._task_id(model_name, "create_meta")
                tasks[inherited_json_task_id] = {
                    "task_id": inherited_json_task_id,
                    "name": "create_meta",
                    "params": {
                        "name": model_name,
                        "domain": domain,
                        "desc": desc,
                        "base_json": str(project_path / domain / base_model_name / f"{base_model_name}.json"),
                        "output": str(project_path / domain / base_model_name / model_name / f"{model_name}.json"),
                        "use_rag": use_rag,
                        "property_catalog": property_catalog,
                        **self._required_contract_params(model_name),
                        **self._llm_params("create_meta"),
                    },
                    "dependencies": [base_json_task_id],
                    "max_retries": self.max_generation_attempts,
                }

                inherited_template_task_id = self._task_id(model_name, "create_template")
                tasks[inherited_template_task_id] = {
                    "task_id": inherited_template_task_id,
                    "name": "create_template",
                    "params": {
                        "name": model_name,
                        "json": str(project_path / domain / base_model_name / model_name / f"{model_name}.json"),
                        "output": str(project_path / domain / base_model_name / model_name / f"{model_name}.template.py")
                    },
                    "dependencies": [inherited_json_task_id],
                    "max_retries": 1,
                }

                inherited_py_task_id = self._task_id(model_name, "complete_code")
                tasks[inherited_py_task_id] = {
                    "task_id": inherited_py_task_id,
                    "name": "complete_code",
                    "params": {
                        "template": str(project_path / domain / base_model_name / model_name / f"{model_name}.template.py"),
                        "output": str(project_path / domain / base_model_name / model_name / f"{model_name}.py"),
                        "base_code": str(project_path / domain / base_model_name / f"{base_model_name}.py"),
                        "name": model_name,
                        "domain": domain,
                        "desc": desc,
                        "use_rag": use_rag,
                        "property_catalog": property_catalog,
                        **self._llm_params("complete_code"),
                    },
                    "dependencies": [
                        inherited_template_task_id,
                        base_py_task_id,
                    ],
                    "max_retries": self.max_generation_attempts,
                }

                inherited_verify_task_id = self._task_id(model_name, "verify_code")
                tasks[inherited_verify_task_id] = {
                    "task_id": inherited_verify_task_id,
                    "name": "verify_code",
                    "params": {
                        "name": model_name,
                        "py": str(project_path / domain / base_model_name / model_name / f"{model_name}.py"),
                        "output": str(project_path / domain / base_model_name / model_name / f"{model_name}_test.py"),
                        "use_rag": use_rag,
                        "domain": domain,
                        "specification": str(
                            project_path
                            / domain
                            / base_model_name
                            / model_name
                            / f"{model_name}.json"
                        ),
                        "property_catalog": property_catalog,
                        "candidate_root": str(project_path / domain),
                        **self._llm_params("verify_code"),
                    },
                    "dependencies": [inherited_py_task_id],
                    "max_retries": self.max_generation_attempts,
                }

        return tasks

if __name__ == '__main__':
    planner = TaskPlanner(
        config.RUN_DIR / "Home-default" / "model_creation",
        output_root=config.DEVICES_DIR / "Home-default",
    )
    type_list_file = config.DEVICES_DIR / "Home-default" / "type_list.json"
    print_run_config(
        "Task planning",
        (
            ("Type list", type_list_file),
            ("Output root", planner.tasks_dir),
        ),
    )
    plan_file_path = planner.create_task_plan(type_list_file)
    print_run_summary(
        "Task planning",
        "PASS",
        (("Plan", plan_file_path),),
    )
