"""
Deployment Intelligence Module
Automated deployment monitoring, failure analysis, and intelligent rollback suggestions
"""

import asyncio
import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import sqlite3
import requests
import yaml
from dataclasses import dataclass
from pathlib import Path
import docker
import kubernetes
from kubernetes import client, config
import boto3
import subprocess
import threading
import time
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

@dataclass
class DeploymentEvent:
    """Represents a deployment event"""
    deployment_id: str
    environment: str  # 'dev', 'staging', 'production'
    application: str
    version: str
    status: str  # 'deploying', 'success', 'failed', 'rolled_back'
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    triggered_by: str
    commit_hash: str
    branch: str

@dataclass
class DeploymentMetric:
    """Deployment performance metric"""
    metric_id: str
    deployment_id: str
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    threshold_breached: bool

@dataclass
class HealthCheck:
    """Application health check result"""
    check_id: str
    deployment_id: str
    check_type: str  # 'http', 'database', 'redis', 'custom'
    status: str  # 'healthy', 'unhealthy', 'degraded'
    response_time_ms: float
    error_message: Optional[str]
    timestamp: datetime

@dataclass
class RollbackSuggestion:
    """Intelligent rollback suggestion"""
    suggestion_id: str
    deployment_id: str
    confidence_score: float
    reason: str
    recommended_action: str  # 'immediate_rollback', 'gradual_rollback', 'monitor', 'fix_forward'
    target_version: Optional[str]
    estimated_impact: str
    automated_rollback_safe: bool

class CloudProviderMonitor:
    """Monitor deployments across different cloud providers"""
    
    def __init__(self):
        self.aws_client = None
        self.k8s_client = None
        self.docker_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize cloud provider clients"""
        try:
            # AWS
            if os.getenv('AWS_ACCESS_KEY_ID'):
                self.aws_client = boto3.client('ecs')
                logger.info("AWS ECS client initialized")
        except Exception as e:
            logger.warning(f"Could not initialize AWS client: {e}")
        
        try:
            # Kubernetes
            if os.path.exists(os.path.expanduser("~/.kube/config")):
                config.load_kube_config()
                self.k8s_client = client.AppsV1Api()
                logger.info("Kubernetes client initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Kubernetes client: {e}")
        
        try:
            # Docker
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Docker client: {e}")
    
    async def get_kubernetes_deployments(self) -> List[Dict[str, Any]]:
        """Get Kubernetes deployment status"""
        deployments = []
        
        try:
            if not self.k8s_client:
                return deployments
            
            # Get all deployments
            v1_deployments = self.k8s_client.list_deployment_for_all_namespaces()
            
            for deployment in v1_deployments.items:
                deployments.append({
                    'name': deployment.metadata.name,
                    'namespace': deployment.metadata.namespace,
                    'replicas': deployment.spec.replicas,
                    'ready_replicas': deployment.status.ready_replicas or 0,
                    'available_replicas': deployment.status.available_replicas or 0,
                    'updated_replicas': deployment.status.updated_replicas or 0,
                    'creation_timestamp': deployment.metadata.creation_timestamp.isoformat(),
                    'image': deployment.spec.template.spec.containers[0].image if deployment.spec.template.spec.containers else None,
                    'conditions': [
                        {
                            'type': condition.type,
                            'status': condition.status,
                            'reason': condition.reason,
                            'message': condition.message
                        }
                        for condition in (deployment.status.conditions or [])
                    ]
                })
            
        except Exception as e:
            logger.error(f"Error getting Kubernetes deployments: {e}")
        
        return deployments
    
    async def get_aws_ecs_services(self) -> List[Dict[str, Any]]:
        """Get AWS ECS service status"""
        services = []
        
        try:
            if not self.aws_client:
                return services
            
            # List all clusters
            clusters = self.aws_client.list_clusters()
            
            for cluster in clusters['clusterArns']:
                # List services in cluster
                cluster_services = self.aws_client.list_services(cluster=cluster)
                
                if cluster_services['serviceArns']:
                    # Describe services
                    service_details = self.aws_client.describe_services(
                        cluster=cluster,
                        services=cluster_services['serviceArns']
                    )
                    
                    for service in service_details['services']:
                        services.append({
                            'cluster': cluster.split('/')[-1],
                            'service_name': service['serviceName'],
                            'status': service['status'],
                            'running_count': service['runningCount'],
                            'pending_count': service['pendingCount'],
                            'desired_count': service['desiredCount'],
                            'task_definition': service['taskDefinition'],
                            'platform_version': service.get('platformVersion'),
                            'created_at': service['createdAt'].isoformat(),
                            'deployments': [
                                {
                                    'id': dep['id'],
                                    'status': dep['status'],
                                    'task_definition': dep['taskDefinition'],
                                    'desired_count': dep['desiredCount'],
                                    'running_count': dep['runningCount'],
                                    'created_at': dep['createdAt'].isoformat()
                                }
                                for dep in service['deployments']
                            ]
                        })
            
        except Exception as e:
            logger.error(f"Error getting AWS ECS services: {e}")
        
        return services
    
    async def get_docker_containers(self) -> List[Dict[str, Any]]:
        """Get Docker container status"""
        containers = []
        
        try:
            if not self.docker_client:
                return containers
            
            for container in self.docker_client.containers.list(all=True):
                containers.append({
                    'id': container.id[:12],
                    'name': container.name,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'status': container.status,
                    'created': container.attrs['Created'],
                    'ports': container.ports,
                    'labels': container.labels,
                    'environment': container.attrs['Config'].get('Env', [])
                })
            
        except Exception as e:
            logger.error(f"Error getting Docker containers: {e}")
        
        return containers

class MetricsCollector:
    """Collect deployment and application metrics"""
    
    def __init__(self):
        self.metrics_endpoints = []
        self.custom_checks = []
    
    async def collect_application_metrics(self, deployment_id: str, app_urls: List[str]) -> List[DeploymentMetric]:
        """Collect application performance metrics"""
        metrics = []
        timestamp = datetime.now()
        
        for url in app_urls:
            try:
                # HTTP response time
                start_time = time.time()
                response = requests.get(url, timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                metrics.append(DeploymentMetric(
                    metric_id=f"{deployment_id}_http_response_time_{hash(url)}",
                    deployment_id=deployment_id,
                    metric_name="http_response_time",
                    value=response_time,
                    unit="ms",
                    timestamp=timestamp,
                    threshold_breached=response_time > 2000  # 2 second threshold
                ))
                
                # HTTP status
                metrics.append(DeploymentMetric(
                    metric_id=f"{deployment_id}_http_status_{hash(url)}",
                    deployment_id=deployment_id,
                    metric_name="http_status_code",
                    value=float(response.status_code),
                    unit="code",
                    timestamp=timestamp,
                    threshold_breached=response.status_code >= 400
                ))
                
            except Exception as e:
                logger.error(f"Error collecting metrics for {url}: {e}")
                # Record failure metric
                metrics.append(DeploymentMetric(
                    metric_id=f"{deployment_id}_http_error_{hash(url)}",
                    deployment_id=deployment_id,
                    metric_name="http_error",
                    value=1.0,
                    unit="boolean",
                    timestamp=timestamp,
                    threshold_breached=True
                ))
        
        return metrics
    
    async def run_health_checks(self, deployment_id: str, health_config: Dict[str, Any]) -> List[HealthCheck]:
        """Run comprehensive health checks"""
        checks = []
        timestamp = datetime.now()
        
        # HTTP health checks
        for http_check in health_config.get('http_checks', []):
            try:
                start_time = time.time()
                response = requests.get(
                    http_check['url'], 
                    timeout=http_check.get('timeout', 5),
                    headers=http_check.get('headers', {})
                )
                response_time = (time.time() - start_time) * 1000
                
                status = 'healthy' if response.status_code == 200 else 'unhealthy'
                error_message = None if status == 'healthy' else f"HTTP {response.status_code}"
                
                checks.append(HealthCheck(
                    check_id=f"{deployment_id}_http_{hash(http_check['url'])}",
                    deployment_id=deployment_id,
                    check_type='http',
                    status=status,
                    response_time_ms=response_time,
                    error_message=error_message,
                    timestamp=timestamp
                ))
                
            except Exception as e:
                checks.append(HealthCheck(
                    check_id=f"{deployment_id}_http_{hash(http_check['url'])}",
                    deployment_id=deployment_id,
                    check_type='http',
                    status='unhealthy',
                    response_time_ms=0.0,
                    error_message=str(e),
                    timestamp=timestamp
                ))
        
        # Database health checks
        for db_check in health_config.get('database_checks', []):
            try:
                # This would need specific database connectors
                # For now, just simulate
                checks.append(HealthCheck(
                    check_id=f"{deployment_id}_db_{hash(db_check['name'])}",
                    deployment_id=deployment_id,
                    check_type='database',
                    status='healthy',  # Would implement actual DB check
                    response_time_ms=50.0,
                    error_message=None,
                    timestamp=timestamp
                ))
                
            except Exception as e:
                checks.append(HealthCheck(
                    check_id=f"{deployment_id}_db_{hash(db_check['name'])}",
                    deployment_id=deployment_id,
                    check_type='database',
                    status='unhealthy',
                    response_time_ms=0.0,
                    error_message=str(e),
                    timestamp=timestamp
                ))
        
        return checks

class IntelligentRollbackEngine:
    """AI-powered rollback decision engine"""
    
    def __init__(self):
        self.failure_patterns = []
        self.historical_data = []
        self.confidence_threshold = 0.7
    
    def analyze_deployment_health(self, 
                                 deployment: DeploymentEvent,
                                 metrics: List[DeploymentMetric],
                                 health_checks: List[HealthCheck]) -> RollbackSuggestion:
        """Analyze deployment health and suggest rollback actions"""
        
        # Calculate health scores
        metrics_score = self._calculate_metrics_score(metrics)
        health_score = self._calculate_health_score(health_checks)
        duration_score = self._calculate_duration_score(deployment)
        
        # Overall confidence score
        overall_score = (metrics_score + health_score + duration_score) / 3
        confidence = 1.0 - overall_score  # Higher problems = higher confidence in rollback
        
        # Determine recommendation
        if confidence >= 0.9:
            action = "immediate_rollback"
            reason = "Critical failures detected: immediate rollback required"
        elif confidence >= 0.7:
            action = "gradual_rollback"
            reason = "Significant issues detected: gradual rollback recommended"
        elif confidence >= 0.5:
            action = "monitor"
            reason = "Some issues detected: continue monitoring closely"
        else:
            action = "fix_forward"
            reason = "Minor issues detected: fix forward recommended"
        
        # Determine target version
        target_version = self._get_last_stable_version(deployment)
        
        return RollbackSuggestion(
            suggestion_id=f"rollback_{deployment.deployment_id}_{int(time.time())}",
            deployment_id=deployment.deployment_id,
            confidence_score=confidence,
            reason=reason,
            recommended_action=action,
            target_version=target_version,
            estimated_impact=self._estimate_rollback_impact(deployment, action),
            automated_rollback_safe=confidence >= 0.8 and action in ["immediate_rollback", "gradual_rollback"]
        )
    
    def _calculate_metrics_score(self, metrics: List[DeploymentMetric]) -> float:
        """Calculate score based on deployment metrics (0 = perfect, 1 = terrible)"""
        if not metrics:
            return 0.5
        
        threshold_breaches = sum(1 for m in metrics if m.threshold_breached)
        return min(threshold_breaches / len(metrics), 1.0)
    
    def _calculate_health_score(self, health_checks: List[HealthCheck]) -> float:
        """Calculate score based on health checks (0 = perfect, 1 = terrible)"""
        if not health_checks:
            return 0.5
        
        unhealthy_count = sum(1 for h in health_checks if h.status == 'unhealthy')
        degraded_count = sum(1 for h in health_checks if h.status == 'degraded')
        
        # Weight unhealthy more than degraded
        problem_score = (unhealthy_count * 1.0 + degraded_count * 0.5) / len(health_checks)
        return min(problem_score, 1.0)
    
    def _calculate_duration_score(self, deployment: DeploymentEvent) -> float:
        """Calculate score based on deployment duration (0 = normal, 1 = too long)"""
        if not deployment.duration_seconds:
            # If still deploying, check elapsed time
            elapsed = (datetime.now() - deployment.start_time).total_seconds()
            # Consider deployments > 30 minutes as problematic
            return min(elapsed / 1800, 1.0)
        
        # Consider deployments > 15 minutes as problematic
        return min(deployment.duration_seconds / 900, 1.0)
    
    def _get_last_stable_version(self, deployment: DeploymentEvent) -> Optional[str]:
        """Get the last known stable version for rollback"""
        # This would query deployment history
        # For now, return a simulated previous version
        try:
            current_version = deployment.version
            if current_version.startswith('v'):
                version_num = int(current_version[1:])
                return f"v{version_num - 1}"
            else:
                return "previous"
        except:
            return "previous"
    
    def _estimate_rollback_impact(self, deployment: DeploymentEvent, action: str) -> str:
        """Estimate the impact of performing a rollback"""
        if action == "immediate_rollback":
            return "High impact: Brief service interruption during rollback"
        elif action == "gradual_rollback":
            return "Medium impact: Gradual traffic migration, minimal interruption"
        elif action == "monitor":
            return "Low impact: Continue monitoring, no immediate action"
        else:
            return "Low impact: Fix issues in current version"

class DeploymentIntelligence:
    """Main deployment intelligence service"""
    
    def __init__(self, db_path: str = "data/deployment_intelligence.db"):
        self.db_path = db_path
        self.cloud_monitor = CloudProviderMonitor()
        self.metrics_collector = MetricsCollector()
        self.rollback_engine = IntelligentRollbackEngine()
        
        self.active_deployments: Dict[str, DeploymentEvent] = {}
        self.monitoring_thread = None
        self.is_monitoring = False
        
        self._init_database()
    
    def _init_database(self):
        """Initialize deployment intelligence database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Deployment events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deployment_events (
                    deployment_id TEXT PRIMARY KEY,
                    environment TEXT,
                    application TEXT,
                    version TEXT,
                    status TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration_seconds REAL,
                    triggered_by TEXT,
                    commit_hash TEXT,
                    branch TEXT
                )
            ''')
            
            # Deployment metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deployment_metrics (
                    metric_id TEXT PRIMARY KEY,
                    deployment_id TEXT,
                    metric_name TEXT,
                    value REAL,
                    unit TEXT,
                    timestamp TEXT,
                    threshold_breached BOOLEAN
                )
            ''')
            
            # Health checks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_checks (
                    check_id TEXT PRIMARY KEY,
                    deployment_id TEXT,
                    check_type TEXT,
                    status TEXT,
                    response_time_ms REAL,
                    error_message TEXT,
                    timestamp TEXT
                )
            ''')
            
            # Rollback suggestions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rollback_suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    deployment_id TEXT,
                    confidence_score REAL,
                    reason TEXT,
                    recommended_action TEXT,
                    target_version TEXT,
                    estimated_impact TEXT,
                    automated_rollback_safe BOOLEAN,
                    timestamp TEXT,
                    executed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing deployment database: {e}")
    
    async def start_deployment_monitoring(self, deployment_config: Dict[str, Any]) -> str:
        """Start monitoring a new deployment"""
        try:
            deployment_id = f"deploy_{int(time.time())}_{deployment_config.get('application', 'app')}"
            
            deployment = DeploymentEvent(
                deployment_id=deployment_id,
                environment=deployment_config.get('environment', 'unknown'),
                application=deployment_config.get('application', 'unknown'),
                version=deployment_config.get('version', 'unknown'),
                status='deploying',
                start_time=datetime.now(),
                end_time=None,
                duration_seconds=None,
                triggered_by=deployment_config.get('triggered_by', 'unknown'),
                commit_hash=deployment_config.get('commit_hash', 'unknown'),
                branch=deployment_config.get('branch', 'unknown')
            )
            
            self.active_deployments[deployment_id] = deployment
            self._save_deployment_event(deployment)
            
            # Start monitoring if not already running
            if not self.is_monitoring:
                self.start_continuous_monitoring()
            
            logger.info(f"Started monitoring deployment: {deployment_id}")
            return deployment_id
            
        except Exception as e:
            logger.error(f"Error starting deployment monitoring: {e}")
            return ""
    
    async def complete_deployment(self, deployment_id: str, status: str) -> Dict[str, Any]:
        """Mark deployment as complete and generate final analysis"""
        try:
            if deployment_id not in self.active_deployments:
                return {"error": "Deployment not found"}
            
            deployment = self.active_deployments[deployment_id]
            deployment.status = status
            deployment.end_time = datetime.now()
            deployment.duration_seconds = (deployment.end_time - deployment.start_time).total_seconds()
            
            self._save_deployment_event(deployment)
            
            # Generate final analysis
            analysis = await self._generate_deployment_analysis(deployment_id)
            
            # Remove from active deployments
            del self.active_deployments[deployment_id]
            
            logger.info(f"Completed deployment monitoring: {deployment_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error completing deployment: {e}")
            return {"error": str(e)}
    
    def start_continuous_monitoring(self):
        """Start continuous monitoring thread"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            logger.info("Started continuous deployment monitoring")
    
    def stop_continuous_monitoring(self):
        """Stop continuous monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        logger.info("Stopped continuous deployment monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Monitor active deployments
                for deployment_id, deployment in list(self.active_deployments.items()):
                    asyncio.create_task(self._monitor_deployment(deployment_id))
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    async def _monitor_deployment(self, deployment_id: str):
        """Monitor a specific deployment"""
        try:
            deployment = self.active_deployments.get(deployment_id)
            if not deployment:
                return
            
            # Collect metrics
            app_urls = [f"http://localhost:8000/health"]  # Would be configured per deployment
            metrics = await self.metrics_collector.collect_application_metrics(deployment_id, app_urls)
            
            # Run health checks
            health_config = {
                'http_checks': [
                    {'url': 'http://localhost:8000/health', 'timeout': 5}
                ],
                'database_checks': [
                    {'name': 'primary_db', 'connection_string': 'postgresql://...'}
                ]
            }
            health_checks = await self.metrics_collector.run_health_checks(deployment_id, health_config)
            
            # Store metrics and health checks
            for metric in metrics:
                self._save_metric(metric)
            for check in health_checks:
                self._save_health_check(check)
            
            # Analyze for rollback recommendations
            suggestion = self.rollback_engine.analyze_deployment_health(deployment, metrics, health_checks)
            self._save_rollback_suggestion(suggestion)
            
            # Execute automatic rollback if conditions are met
            if suggestion.automated_rollback_safe and suggestion.recommended_action == "immediate_rollback":
                await self._execute_automatic_rollback(deployment_id, suggestion)
            
        except Exception as e:
            logger.error(f"Error monitoring deployment {deployment_id}: {e}")
    
    async def _execute_automatic_rollback(self, deployment_id: str, suggestion: RollbackSuggestion):
        """Execute automatic rollback"""
        try:
            logger.warning(f"Executing automatic rollback for {deployment_id}: {suggestion.reason}")
            
            # This would integrate with actual deployment systems
            # For now, just update the deployment status
            deployment = self.active_deployments.get(deployment_id)
            if deployment:
                deployment.status = 'rolled_back'
                self._save_deployment_event(deployment)
            
            # Mark suggestion as executed
            suggestion_dict = {
                'suggestion_id': suggestion.suggestion_id,
                'executed': True,
                'timestamp': datetime.now().isoformat()
            }
            
            # Log the rollback action
            logger.info(f"Automatic rollback completed for {deployment_id}")
            
        except Exception as e:
            logger.error(f"Error executing automatic rollback: {e}")
    
    async def _generate_deployment_analysis(self, deployment_id: str) -> Dict[str, Any]:
        """Generate comprehensive deployment analysis"""
        try:
            # Get deployment data
            deployment = self.active_deployments.get(deployment_id)
            metrics = self._get_metrics_for_deployment(deployment_id)
            health_checks = self._get_health_checks_for_deployment(deployment_id)
            suggestions = self._get_rollback_suggestions_for_deployment(deployment_id)
            
            # Calculate summary statistics
            total_metrics = len(metrics)
            failed_metrics = sum(1 for m in metrics if m.threshold_breached)
            
            total_checks = len(health_checks)
            failed_checks = sum(1 for h in health_checks if h.status == 'unhealthy')
            
            analysis = {
                'deployment_id': deployment_id,
                'deployment_info': {
                    'environment': deployment.environment if deployment else 'unknown',
                    'application': deployment.application if deployment else 'unknown',
                    'version': deployment.version if deployment else 'unknown',
                    'status': deployment.status if deployment else 'unknown',
                    'duration_seconds': deployment.duration_seconds if deployment else 0
                },
                'metrics_summary': {
                    'total_metrics': total_metrics,
                    'failed_metrics': failed_metrics,
                    'success_rate': ((total_metrics - failed_metrics) / total_metrics * 100) if total_metrics > 0 else 0
                },
                'health_summary': {
                    'total_checks': total_checks,
                    'failed_checks': failed_checks,
                    'health_score': ((total_checks - failed_checks) / total_checks * 100) if total_checks > 0 else 0
                },
                'rollback_suggestions': len(suggestions),
                'overall_status': 'success' if failed_metrics == 0 and failed_checks == 0 else 'issues_detected',
                'recommendations': [
                    {
                        'action': s.recommended_action,
                        'confidence': s.confidence_score,
                        'reason': s.reason
                    }
                    for s in suggestions
                ]
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating deployment analysis: {e}")
            return {"error": str(e)}
    
    def _save_deployment_event(self, deployment: DeploymentEvent):
        """Save deployment event to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO deployment_events 
                (deployment_id, environment, application, version, status, start_time, 
                 end_time, duration_seconds, triggered_by, commit_hash, branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                deployment.deployment_id,
                deployment.environment,
                deployment.application,
                deployment.version,
                deployment.status,
                deployment.start_time.isoformat(),
                deployment.end_time.isoformat() if deployment.end_time else None,
                deployment.duration_seconds,
                deployment.triggered_by,
                deployment.commit_hash,
                deployment.branch
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving deployment event: {e}")
    
    def _save_metric(self, metric: DeploymentMetric):
        """Save deployment metric to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO deployment_metrics 
                (metric_id, deployment_id, metric_name, value, unit, timestamp, threshold_breached)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.metric_id,
                metric.deployment_id,
                metric.metric_name,
                metric.value,
                metric.unit,
                metric.timestamp.isoformat(),
                metric.threshold_breached
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving metric: {e}")
    
    def _save_health_check(self, check: HealthCheck):
        """Save health check result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO health_checks 
                (check_id, deployment_id, check_type, status, response_time_ms, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                check.check_id,
                check.deployment_id,
                check.check_type,
                check.status,
                check.response_time_ms,
                check.error_message,
                check.timestamp.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving health check: {e}")
    
    def _save_rollback_suggestion(self, suggestion: RollbackSuggestion):
        """Save rollback suggestion to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO rollback_suggestions 
                (suggestion_id, deployment_id, confidence_score, reason, recommended_action, 
                 target_version, estimated_impact, automated_rollback_safe, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                suggestion.suggestion_id,
                suggestion.deployment_id,
                suggestion.confidence_score,
                suggestion.reason,
                suggestion.recommended_action,
                suggestion.target_version,
                suggestion.estimated_impact,
                suggestion.automated_rollback_safe,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving rollback suggestion: {e}")
    
    def _get_metrics_for_deployment(self, deployment_id: str) -> List[DeploymentMetric]:
        """Get all metrics for a deployment"""
        metrics = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM deployment_metrics WHERE deployment_id = ?', (deployment_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                metrics.append(DeploymentMetric(
                    metric_id=row[0],
                    deployment_id=row[1],
                    metric_name=row[2],
                    value=row[3],
                    unit=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    threshold_breached=bool(row[6])
                ))
            
            conn.close()
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
        
        return metrics
    
    def _get_health_checks_for_deployment(self, deployment_id: str) -> List[HealthCheck]:
        """Get all health checks for a deployment"""
        checks = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM health_checks WHERE deployment_id = ?', (deployment_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                checks.append(HealthCheck(
                    check_id=row[0],
                    deployment_id=row[1],
                    check_type=row[2],
                    status=row[3],
                    response_time_ms=row[4],
                    error_message=row[5],
                    timestamp=datetime.fromisoformat(row[6])
                ))
            
            conn.close()
        except Exception as e:
            logger.error(f"Error getting health checks: {e}")
        
        return checks
    
    def _get_rollback_suggestions_for_deployment(self, deployment_id: str) -> List[RollbackSuggestion]:
        """Get all rollback suggestions for a deployment"""
        suggestions = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM rollback_suggestions WHERE deployment_id = ?', (deployment_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                suggestions.append(RollbackSuggestion(
                    suggestion_id=row[0],
                    deployment_id=row[1],
                    confidence_score=row[2],
                    reason=row[3],
                    recommended_action=row[4],
                    target_version=row[5],
                    estimated_impact=row[6],
                    automated_rollback_safe=bool(row[7])
                ))
            
            conn.close()
        except Exception as e:
            logger.error(f"Error getting rollback suggestions: {e}")
        
        return suggestions

# Initialize global deployment intelligence service
deployment_intelligence = DeploymentIntelligence()

if __name__ == "__main__":
    # Test the deployment intelligence system
    async def test_deployment_intelligence():
        service = DeploymentIntelligence()
        
        # Start monitoring a deployment
        deployment_config = {
            'environment': 'production',
            'application': 'mentor-app',
            'version': 'v1.2.3',
            'triggered_by': 'github-actions',
            'commit_hash': 'abc123',
            'branch': 'main'
        }
        
        deployment_id = await service.start_deployment_monitoring(deployment_config)
        print(f"Started monitoring deployment: {deployment_id}")
        
        # Simulate monitoring for a bit
        await asyncio.sleep(5)
        
        # Complete deployment
        analysis = await service.complete_deployment(deployment_id, 'success')
        print(f"Deployment analysis: {json.dumps(analysis, indent=2)}")
        
        service.stop_continuous_monitoring()
    
    # Run test
    asyncio.run(test_deployment_intelligence())
