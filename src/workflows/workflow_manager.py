"""
Workflow Manager - Manages system workflows and coordination
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from ..messaging.message_bus import MessageBus
from ..interfaces.agent_interface import Message, MessageType

class WorkflowStatus(Enum):
    """Workflow status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowStep:
    """Workflow step definition"""
    name: str
    agent_id: str
    message_type: MessageType
    data: Dict[str, Any]
    timeout: float = 30.0
    retry_count: int = 3
    requires_response: bool = True

@dataclass
class Workflow:
    """Workflow definition"""
    name: str
    description: str
    steps: List[WorkflowStep]
    parallel: bool = False
    timeout: float = 300.0
    
@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    workflow_id: str
    workflow: Workflow
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    current_step: int = 0
    results: Dict[str, Any] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}
        if self.errors is None:
            self.errors = []

class WorkflowManager:
    """Manages system workflows and coordination"""
    
    def __init__(self):
        self.logger = logging.getLogger("workflow_manager")
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.message_bus: Optional[MessageBus] = None
        self.running_workflows: Dict[str, asyncio.Task] = {}
        
    async def initialize(self, message_bus: MessageBus):
        """Initialize workflow manager"""
        self.message_bus = message_bus
        await self._load_default_workflows()
        self.logger.info("Workflow manager initialized")
        
    async def start(self):
        """Start workflow manager"""
        self.logger.info("Workflow manager started")
        
    async def stop(self):
        """Stop workflow manager"""
        # Cancel all running workflows
        for workflow_id, task in self.running_workflows.items():
            task.cancel()
            self.logger.info(f"Cancelled workflow: {workflow_id}")
            
        self.running_workflows.clear()
        self.logger.info("Workflow manager stopped")
        
    def register_workflow(self, workflow: Workflow):
        """Register workflow"""
        self.workflows[workflow.name] = workflow
        self.logger.info(f"Registered workflow: {workflow.name}")
        
    async def execute_workflow(self, workflow_name: str, parameters: Dict[str, Any] = None) -> str:
        """Execute workflow"""
        try:
            workflow = self.workflows.get(workflow_name)
            if not workflow:
                raise ValueError(f"Workflow not found: {workflow_name}")
                
            # Create execution instance
            workflow_id = f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                workflow=workflow,
                status=WorkflowStatus.PENDING,
                start_time=datetime.now()
            )
            
            self.executions[workflow_id] = execution
            
            # Start execution
            task = asyncio.create_task(self._execute_workflow(execution, parameters or {}))
            self.running_workflows[workflow_id] = task
            
            self.logger.info(f"Started workflow execution: {workflow_id}")
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_name}: {e}")
            raise
            
    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status"""
        return self.executions.get(workflow_id)
        
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel workflow execution"""
        try:
            execution = self.executions.get(workflow_id)
            if not execution:
                return False
                
            # Cancel task
            task = self.running_workflows.get(workflow_id)
            if task:
                task.cancel()
                del self.running_workflows[workflow_id]
                
            # Update status
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = datetime.now()
            
            self.logger.info(f"Cancelled workflow: {workflow_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling workflow {workflow_id}: {e}")
            return False
            
    async def _execute_workflow(self, execution: WorkflowExecution, parameters: Dict[str, Any]):
        """Execute workflow steps"""
        try:
            execution.status = WorkflowStatus.RUNNING
            
            if execution.workflow.parallel:
                await self._execute_parallel_workflow(execution, parameters)
            else:
                await self._execute_sequential_workflow(execution, parameters)
                
            execution.status = WorkflowStatus.COMPLETED
            execution.end_time = datetime.now()
            
            self.logger.info(f"Workflow completed: {execution.workflow_id}")
            
        except asyncio.CancelledError:
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = datetime.now()
            self.logger.info(f"Workflow cancelled: {execution.workflow_id}")
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.end_time = datetime.now()
            execution.errors.append(str(e))
            self.logger.error(f"Workflow failed: {execution.workflow_id} - {e}")
            
        finally:
            # Remove from running workflows
            if execution.workflow_id in self.running_workflows:
                del self.running_workflows[execution.workflow_id]
                
    async def _execute_sequential_workflow(self, execution: WorkflowExecution, parameters: Dict[str, Any]):
        """Execute workflow steps sequentially"""
        for i, step in enumerate(execution.workflow.steps):
            execution.current_step = i
            
            try:
                result = await self._execute_step(step, parameters)
                execution.results[step.name] = result
                
            except Exception as e:
                execution.errors.append(f"Step {step.name} failed: {e}")
                raise
                
    async def _execute_parallel_workflow(self, execution: WorkflowExecution, parameters: Dict[str, Any]):
        """Execute workflow steps in parallel"""
        tasks = []
        
        for step in execution.workflow.steps:
            task = asyncio.create_task(self._execute_step(step, parameters))
            tasks.append((step.name, task))
            
        # Wait for all tasks to complete
        for step_name, task in tasks:
            try:
                result = await task
                execution.results[step_name] = result
                
            except Exception as e:
                execution.errors.append(f"Step {step_name} failed: {e}")
                
    async def _execute_step(self, step: WorkflowStep, parameters: Dict[str, Any]) -> Any:
        """Execute individual workflow step"""
        try:
            # Merge step data with parameters
            message_data = {**step.data, **parameters}
            
            # Create message
            from ..factories.message_factory import MessageFactory
            message_factory = MessageFactory()
            
            message = message_factory.create_message(
                message_type=step.message_type,
                sender="workflow_manager",
                recipient=step.agent_id,
                data=message_data,
                requires_response=step.requires_response
            )
            
            # Send message and wait for response
            if step.requires_response:
                response = await asyncio.wait_for(
                    self.message_bus.send_message(message),
                    timeout=step.timeout
                )
                
                if response and response.data.get("success", False):
                    return response.data
                else:
                    raise Exception(f"Step failed: {response.data.get('error', 'Unknown error')}")
            else:
                await self.message_bus.publish(message)
                return {"status": "published"}
                
        except asyncio.TimeoutError:
            raise Exception(f"Step {step.name} timed out")
            
    async def _load_default_workflows(self):
        """Load default workflows"""
        try:
            from .default_workflows import get_default_workflows
            workflows = get_default_workflows()
            
            for workflow in workflows.values():
                self.register_workflow(workflow)
                
            self.logger.info(f"Loaded {len(workflows)} default workflows")
            
        except Exception as e:
            self.logger.error(f"Error loading default workflows: {e}")
            # Fallback to basic workflows
            await self._load_basic_workflows()
    
    async def _load_basic_workflows(self):
        """Load basic fallback workflows"""
        # System health check workflow
        health_check_workflow = Workflow(
            name="health_check",
            description="Perform system health check",
            steps=[
                WorkflowStep(
                    name="check_agents",
                    agent_id="orchestrator",
                    message_type=MessageType.HEALTH_CHECK,
                    data={"check_type": "full"}
                ),
                WorkflowStep(
                    name="test_message_bus",
                    agent_id="testing_agent",
                    message_type=MessageType.TEST_REQUEST,
                    data={"test_type": "integration", "component": "message_bus"}
                )
            ],
            parallel=True
        )
        
        self.register_workflow(health_check_workflow)
        
    async def get_status(self) -> Dict[str, Any]:
        """Get workflow manager status"""
        return {
            "registered_workflows": list(self.workflows.keys()),
            "running_workflows": list(self.running_workflows.keys()),
            "total_executions": len(self.executions),
            "active_executions": len([e for e in self.executions.values() if e.status == WorkflowStatus.RUNNING])
        }
