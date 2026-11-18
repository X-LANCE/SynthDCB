from dataclasses import dataclass, field
from typing import Generic, Tuple, TypeVar, Optional, List, Any
import math
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

T = TypeVar("T")

@dataclass
class BaseProperty(Generic[T]):
    """
    Generic typed container with built-in validation and set_*/get_* helpers.
    Subclasses must implement `validate(self, value: T) -> str`.
    """
    name: str
    default: T
    value: Optional[T] = None # field(init=False, repr=False)
    mode: int = 3
    current_mode: int = mode
    previous_mode: int = mode
    auto_reset: bool = False
    unit: Optional[str] = None
    description: Optional[str] = None
    allow_none: bool = False
    
    def __post_init__(self) -> None:
        """Initialize the value and access modes after dataclass construction."""
        self.value = self.default
        self.current_mode = self.mode
        self.previous_mode = self.mode
    
    def get(self) -> Tuple[str, Optional[T] | None]:
        """get_* template: return the current value."""
        if not self.current_mode // 2:
            return f"[READ_ERROR] {self.name}: property is not readable", None
        return "[PASS]",self.value
    
    def set(self,
            value: Optional[T]) -> str:
        """set_* template: validate then set the value."""
        if not self.current_mode % 2 :
            return f"[WRITE_ERROR] {self.name}: property is not writable"
        if value is None:
            if not self.allow_none:
                return f"[VALIDATION_ERROR] {self.name}: None is not allowed"
            self.value = None
            return "[PASS]"
        code = self.validate(value)
        if code == "[PASS]":
            self.value = value
        return code

    def internal_set(self,
                     value: Optional[T]) -> str:
        """Set a property from object-internal logic, bypassing public write permission."""
        if value is None:
            if not self.allow_none:
                return f"[VALIDATION_ERROR] {self.name}: None is not allowed"
            self.value = None
            return "[PASS]"
        code = self.validate(value)
        if code == "[PASS]":
            self.value = value
        return code
    
    def chmod(self,
              current_mode: int) -> None:
        """Change the access mode of the property."""
        if current_mode < 0 or current_mode > self.mode:
            raise ValueError(f"Invalid mode {current_mode} for property {self.name}")
        self.current_mode = current_mode
    
    def handle_power_switch(self,
                            on: bool) -> str:
        """Helper to set permission to read/write as well as reset value on power switch."""
        if self.mode == 0:
            return "[NO_ACTION] Property is disabled; no action taken on power switch."
        if self.name.lower() == "power":
            return "[NO_ACTION] You should not call handle_power_switch on the power property itself."
        if on:
            if self.auto_reset:
                self.chmod(self.mode)
                self.reset()
            else:
                self.chmod(self.previous_mode)
        else:
            self.previous_mode = self.current_mode
            self.chmod(0)
        return "[PASS]"
    
    def disable(self) ->None:
        """Disable the property (no read or write). Use when disabling inherited properties. Cannot be re-enabled."""
        self.mode = 0
        self.chmod(0)
    
    def enable(self) -> None:
        """Reject attempts to re-enable a permanently disabled property."""
        raise RuntimeError("disabled properties cannot be re-enabled")
    
    def reset(self) -> None:
        """Reset to default."""
        self.value = self.default
        self.previous_mode = self.mode
        self.current_mode = self.mode
    
    def validate(self,
                 value: T) -> str:
        """Return the validation status for a candidate property value."""
        raise NotImplementedError


# ------------------------------ Typed Properties ------------------------------
@dataclass
class IntProperty(BaseProperty[int]):
    """
    Integer property with optional range and step alignment.
    """
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    step: Optional[int] = None  # if provided, (value - step_origin) % step == 0
    step_origin: Optional[int] = None  # defaults to minimum if set, else 0
    
    def validate(self,
                 value: int) -> str:
        """Return the validation status for a candidate property value."""
        if type(value) is not int:
            return f"[VALIDATION_ERROR] {self.name}: expected int"
        if self.minimum is not None and value < self.minimum:
            return f"[VALIDATION_ERROR] {self.name}: {value} < minimum {self.minimum}"
        if self.maximum is not None and value > self.maximum:
            return f"[VALIDATION_ERROR] {self.name}: {value} > maximum {self.maximum}"
        if self.step is not None:
            if type(self.step) is not int or self.step <= 0:
                return f"[VALIDATION_ERROR] {self.name}: step must be a positive int"
            origin = self.step_origin if self.step_origin is not None else (self.minimum or 0)
            if (value - origin) % self.step != 0:
                return f"[VALIDATION_ERROR] {self.name}: {value} must align to step {self.step} from origin {origin}"
        return "[PASS]"
    
    def increase(self,
                 amount: int = 1) -> str:
        """
        Increase the property value by amount, respecting maximum.
        """
        if self.value is None:
            return f"[VALIDATION_ERROR] {self.name}: cannot increase None value"
        if amount <= 0:
            return f"[VALIDATION_ERROR] {self.name}: increase amount must be positive"
        new_value = self.value + amount
        code = self.set(new_value)
        return code
    
    def decrease(self,
                 amount: int = 1) -> str:
        """
        Decrease the property value by amount, respecting minimum.
        """
        if self.value is None:
            return f"[VALIDATION_ERROR] {self.name}: cannot increase None value"
        if amount <= 0:
            return f"[VALIDATION_ERROR] {self.name}: decrease amount must be positive"
        new_value = self.value - amount
        code = self.set(new_value)
        return code


@dataclass
class FloatProperty(BaseProperty[float]):
    """
    Numeric property with optional range, step alignment, and precision.
    """
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    step_origin: Optional[float] = None
    precision: Optional[int] = None  # number of decimal places (hint)
    
    def validate(self,
                 value: float) -> str:
        """Return the validation status for a candidate property value."""
        if type(value) not in (float, int):
            return f"[VALIDATION_ERROR] {self.name}: expected float"
        value = float(value)
        if self.minimum is not None and value < self.minimum:
            return f"[VALIDATION_ERROR] {self.name}: {value} < minimum {self.minimum}"
        if self.maximum is not None and value > self.maximum:
            return f"[VALIDATION_ERROR] {self.name}: {value} > maximum {self.maximum}"
        if self.step is not None:
            if type(self.step) not in (float, int) or self.step <= 0:
                return f"[VALIDATION_ERROR] {self.name}: step must be positive"
            origin = (
                float(self.step_origin)
                if self.step_origin is not None
                else float(self.minimum or 0.0)
            )
            quotient = (value - origin) / float(self.step)
            if not math.isclose(
                quotient,
                round(quotient),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                return (
                    f"[VALIDATION_ERROR] {self.name}: {value} must align "
                    f"to step {self.step} from origin {origin}"
                )
        if self.precision is not None:
            # precision is a hint; enforce if provided
            scaled = round(value, self.precision)
            if scaled != value:
                return f"[VALIDATION_ERROR] {self.name}: {value} must have at most {self.precision} decimal places"
        return "[PASS]"
    
    def increase(self,
                 amount: float = 1.0) -> str:
        """
        Increase the property value by amount, respecting maximum.
        """
        if self.value is None:
            return f"[VALIDATION_ERROR] {self.name}: cannot increase None value"
        if amount <= 0:
            return f"[VALIDATION_ERROR] {self.name}: increase amount must be positive"
        new_value = self.value + amount
        code = self.set(new_value)
        return code
    
    def decrease(self,
                 amount: float = 1.0) -> str:
        """
        Decrease the property value by amount, respecting minimum.
        """
        if self.value is None:
            return f"[VALIDATION_ERROR] {self.name}: cannot decrease None value"
        if amount <= 0:
            return f"[VALIDATION_ERROR] {self.name}: decrease amount must be positive"
        new_value = self.value - amount
        code = self.set(new_value)
        return code


@dataclass
class StringProperty(BaseProperty[str]):
    """
    String property with optional length and regex constraints.
    """
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # fullmatch regex
    choices: Optional[List[str]] = field(default_factory=list)
    case_sensitive: bool = True
    
    def validate(self,
                 value: str)-> str:
        """Return the validation status for a candidate property value."""
        if not isinstance(value, str):
            return f"[VALIDATION_ERROR] {self.name}: expected str"
        if self.max_length is not None and len(value) > self.max_length:
            return f"[VALIDATION_ERROR] {self.name}: length {len(value)} > max_length {self.max_length}"
        if self.pattern is not None and re.fullmatch(self.pattern, value) is None:
            return f"[VALIDATION_ERROR] {self.name}: '{value}' does not match pattern {self.pattern!r}"
        if self.choices:
            if self.case_sensitive:
                ok = value in self.choices
            else:
                ok = value.lower() in {c.lower() for c in self.choices}
            if not ok:
                return f"[VALIDATION_ERROR] {self.name}: '{value}' not in {self.choices}"
        return "[PASS]"


@dataclass
class BoolProperty(BaseProperty[bool]):
    """
    Boolean property.
    """
    
    def validate(self,
                 value: bool) -> str:
        """Return the validation status for a candidate property value."""
        if type(value) is not bool:  # avoid ints being accepted as bools
            return f"[VALIDATION_ERROR] {self.name}: expected bool"
        return "[PASS]"


@dataclass
class DictProperty(BaseProperty[dict]):
    """
    Dictionary property with schema validation.
    """
    schema: Optional[dict] = None

    def validate(self,
                 value: dict) -> str:
        """Return the validation status for a candidate property value."""
        if not isinstance(value, dict):
            return f"[VALIDATION_ERROR] {self.name}: expected dict"
        if any(not isinstance(key, str) for key in value):
            return f"[VALIDATION_ERROR] {self.name}: dictionary keys must be strings"
        if self.schema:
            try:
                Draft202012Validator.check_schema(self.schema)
                errors = sorted(
                    Draft202012Validator(self.schema).iter_errors(value),
                    key=lambda error: (
                        list(error.absolute_path),
                        error.message,
                    ),
                )
            except SchemaError as error:
                return (
                    f"[VALIDATION_ERROR] {self.name}: "
                    f"invalid property schema: {error}"
                )
            if errors:
                return f"[VALIDATION_ERROR] {self.name}: schema validation failed: {errors}"
        return "[PASS]"
    
    def get_by_key(self,key:str) -> tuple[str, Any]:
        """Get value by key from the dictionary."""
        if not self.current_mode // 2:
            return f"[READ_ERROR] {self.name}: property is not readable", None
        if self.value is None:
            return f"[READ_ERROR] {self.name}: value is None", None
        if key not in self.value:
            return f"[KEY_ERROR] {self.name}: key '{key}' not found", None
        return "[PASS]", self.value[key]
    
    def set_by_key(self,key:str, val) -> str:
        """Set value by key in the dictionary."""
        if not self.current_mode % 2 :
            return f"[WRITE_ERROR] {self.name}: property is not writable"
        if self.value is None:
            return f"[WRITE_ERROR] {self.name}: value is None"
        new_dict = self.value.copy()
        new_dict[key] = val
        code = self.set(new_dict)
        return code
    
    def delete_by_key(self,key:str) -> str:
        """Delete key from the dictionary."""
        if not self.current_mode % 2 :
            return f"[WRITE_ERROR] {self.name}: property is not writable"
        if self.value is None:
            return f"[WRITE_ERROR] {self.name}: value is None"
        if key not in self.value:
            return f"[KEY_ERROR] {self.name}: key '{key}' not found"
        new_dict = self.value.copy()
        del new_dict[key]
        code = self.set(new_dict)
        return code
