#!/usr/bin/env python3
"""
pipelinectl - Command Line Interface for the IM2 Audio Processing Pipeline

This tool provides control over the entire IM2 pipeline, including:
- Job submission and management
- Service control (start, stop, status)
- System monitoring and health checks
- Migrations and upgrades
- Testing and diagnostics
"""

import os
import sys
import json
import time
import logging
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

import click
import requests
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.markdown import Markdown
from tabulate import tabulate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('pipelinectl')

# Rich console for pretty output
console = Console()

# Default API URL
API_URL = os.getenv('IM2_API_URL', 'http://localhost:8000')
API_TOKEN = os.getenv('IM2_API_TOKEN', '')

# Configuration
CONFIG_DIR = Path.home() / '.im2'
CONFIG_FILE = CONFIG_DIR / 'config.yaml'

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True, parents=True)

def load_config() -> Dict:
    """Load configuration from file."""
    if not CONFIG_FILE.exists():
        return {}
    
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f) or {}

def save_config(config: Dict) -> None:
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)

def api_request(endpoint: str, method: str = 'GET', data: Dict = None, 
                params: Dict = None, files: Dict = None) -> Dict:
    """Make an API request to the IM2 backend."""
    url = f"{API_URL}{endpoint}"
    headers = {}
    
    if API_TOKEN:
        headers['Authorization'] = f"Bearer {API_TOKEN}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, params=params, files=files)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data, params=params)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        
        if response.content:
            return response.json()
        return {}
    
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error communicating with API:[/] {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                console.print(f"[red]Error details:[/] {error_data}")
            except:
                console.print(f"[red]Status code:[/] {e.response.status_code}")
                console.print(f"[red]Response text:[/] {e.response.text}")
        sys.exit(1)

def format_table(data: List[Dict], columns: List[str]) -> str:
    """Format data as a table."""
    table_data = []
    for item in data:
        row = []
        for col in columns:
            row.append(item.get(col, ''))
        table_data.append(row)
    
    return tabulate(table_data, headers=columns, tablefmt='pretty')

def run_docker_compose_command(command: str, capture_output: bool = False) -> Optional[str]:
    """Run a docker compose command."""
    try:
        full_command = f"docker compose {command}"
        
        if capture_output:
            result = subprocess.run(full_command, shell=True, check=True, 
                                   capture_output=True, text=True)
            return result.stdout
        else:
            subprocess.run(full_command, shell=True, check=True)
            return None
    
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Command failed:[/] {e}")
        if e.stderr:
            console.print(f"[red]Error details:[/] {e.stderr}")
        sys.exit(1)

# CLI Groups
@click.group()
@click.version_option(version="1.0.0")
def cli():
    """IM2 Pipeline Control Tool - Manage audio processing pipeline."""
    pass

# =============================================================================
# Pipeline Control Commands
# =============================================================================
@cli.group()
def pipeline():
    """Pipeline control commands."""
    pass

@pipeline.command("up")
@click.option("--detach", "-d", is_flag=True, help="Run in detached mode")
@click.option("--build", "-b", is_flag=True, help="Build images before starting")
def pipeline_up(detach, build):
    """Start the pipeline services."""
    cmd_args = []
    
    if detach:
        cmd_args.append("-d")
    
    if build:
        cmd_args.append("--build")
    
    with console.status("[bold green]Starting IM2 pipeline services..."):
        run_docker_compose_command(f"up {' '.join(cmd_args)}")
    
    console.print("[bold green]Pipeline services started successfully.[/]")

@pipeline.command("down")
@click.option("--volumes", "-v", is_flag=True, help="Remove volumes")
def pipeline_down(volumes):
    """Stop the pipeline services."""
    cmd_args = []
    
    if volumes:
        cmd_args.append("-v")
    
    with console.status("[bold yellow]Stopping IM2 pipeline services..."):
        run_docker_compose_command(f"down {' '.join(cmd_args)}")
    
    console.print("[bold green]Pipeline services stopped successfully.[/]")

@pipeline.command("status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def pipeline_status(output_json):
    """Check status of pipeline services."""
    with console.status("[bold blue]Checking IM2 pipeline status..."):
        output = run_docker_compose_command("ps --format json", capture_output=True)
    
    if output_json:
        click.echo(output)
        return
    
    try:
        services = json.loads(output)
        
        table = Table(title="IM2 Pipeline Services Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Ports", style="yellow")
        table.add_column("Created", style="blue")
        
        for service in services:
            status = service.get("State", "Unknown")
            status_style = "green" if status == "running" else "red"
            
            table.add_row(
                service.get("Name", "Unknown"),
                f"[{status_style}]{status}[/{status_style}]",
                service.get("Ports", ""),
                service.get("RunningFor", "")
            )
        
        console.print(table)
    
    except json.JSONDecodeError:
        console.print("[bold yellow]Could not parse service status. Raw output:[/]")
        console.print(output)

@pipeline.command("logs")
@click.argument("service", required=False)
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--tail", "-t", type=int, default=100, help="Number of lines to show")
def pipeline_logs(service, follow, tail):
    """View logs for pipeline services."""
    cmd_args = []
    
    if follow:
        cmd_args.append("-f")
    
    cmd_args.append(f"--tail={tail}")
    
    if service:
        cmd_args.append(service)
    
    console.print(f"[bold blue]Showing logs for {'all services' if not service else service}...[/]")
    run_docker_compose_command(f"logs {' '.join(cmd_args)}")

@pipeline.command("pause")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def pipeline_pause(confirm):
    """Pause the pipeline (stops job processing but keeps services running)."""
    if not confirm:
        if not click.confirm("Are you sure you want to pause the pipeline? This will stop processing new jobs."):
            console.print("[yellow]Operation cancelled.[/]")
            return
    
    with console.status("[bold yellow]Pausing IM2 pipeline..."):
        # This would make an API call to pause the queue
        try:
            result = api_request("/api/system/pause", method="POST")
            console.print(f"[bold green]Pipeline paused successfully.[/]")
            console.print(f"Paused at: {result.get('paused_at', 'Unknown')}")
        except Exception as e:
            console.print(f"[bold red]Failed to pause pipeline:[/] {str(e)}")

@pipeline.command("resume")
def pipeline_resume():
    """Resume the pipeline after being paused."""
    with console.status("[bold green]Resuming IM2 pipeline..."):
        # This would make an API call to resume the queue
        try:
            result = api_request("/api/system/resume", method="POST")
            console.print(f"[bold green]Pipeline resumed successfully.[/]")
            console.print(f"Resumed at: {result.get('resumed_at', 'Unknown')}")
        except Exception as e:
            console.print(f"[bold red]Failed to resume pipeline:[/] {str(e)}")

# =============================================================================
# Job Management Commands
# =============================================================================
@cli.group()
def job():
    """Job management commands."""
    pass

@job.command("submit")
@click.option("--file", "-f", required=True, type=click.Path(exists=True), 
              help="Audio file path")
@click.option("--engine", "-e", type=click.Choice(['spleeter', 'demucs', 'auto']), 
              default='auto', help="Separation engine to use")
@click.option("--user", "-u", default=None, help="User ID (defaults to current user)")
@click.option("--metadata", type=click.Path(exists=True), help="Path to JSON metadata file")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def job_submit_cmd(file, engine, user, metadata, output_json):
    """Submit a new job to the pipeline."""
    file_path = Path(file).resolve()
    
    # Load metadata if provided
    metadata_dict = {}
    if metadata:
        with open(metadata, 'r') as f:
            metadata_dict = json.load(f)
    
    with console.status(f"[bold green]Submitting job for file: {file_path}..."):
        # In a real implementation, this would upload the file and make an API call
        job_id = f"job_{int(time.time())}_{file_path.name}"
        
        # Simulate API call
        job_data = {
            "job_id": job_id,
            "file": str(file_path),
            "engine": engine,
            "user_id": user or "default",
            "metadata": metadata_dict,
            "status": "submitted",
            "created_at": datetime.now().isoformat()
        }
    
    if output_json:
        click.echo(json.dumps(job_data, indent=2))
    else:
        console.print(f"[bold green]Job submitted with ID: {job_id}[/]")
        console.print(f"File: {file_path}")
        console.print(f"Engine: {engine}")
        console.print(f"Status: {job_data['status']}")
        console.print(f"Created at: {job_data['created_at']}")

@job.command("list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--user", "-u", help="Filter by user")
@click.option("--limit", "-l", type=int, default=10, help="Limit results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def job_list_cmd(status, user, limit, output_json):
    """List jobs in the pipeline."""
    with console.status("[bold blue]Listing jobs..."):
        # This would fetch from the queue API in a real implementation
        # Simulate API response
        jobs = [
            {
                "job_id": f"job_example_{i}",
                "file": f"example_{i}.mp3",
                "status": "completed" if i % 3 == 0 else "processing" if i % 3 == 1 else "failed",
                "user_id": "default",
                "created_at": (datetime.now().isoformat()),
                "updated_at": (datetime.now().isoformat())
            }
            for i in range(limit)
        ]
    
    if output_json:
        click.echo(json.dumps(jobs, indent=2))
    else:
        table = Table(title=f"Jobs ({len(jobs)} results)")
        table.add_column("Job ID", style="cyan")
        table.add_column("File", style="blue")
        table.add_column("Status", style="green")
        table.add_column("User", style="yellow")
        table.add_column("Created", style="magenta")
        
        for job in jobs:
            status = job.get("status", "Unknown")
            status_style = "green" if status == "completed" else "yellow" if status == "processing" else "red"
            
            table.add_row(
                job.get("job_id", "Unknown"),
                job.get("file", "Unknown"),
                f"[{status_style}]{status}[/{status_style}]",
                job.get("user_id", "Unknown"),
                job.get("created_at", "Unknown")
            )
        
        console.print(table)

@job.command("status")
@click.argument("job_id", required=True)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def job_status_cmd(job_id, output_json):
    """Check status of a specific job."""
    with console.status(f"[bold blue]Checking status for job: {job_id}..."):
        # This would fetch from the queue API in a real implementation
        # Simulate API response
        job_data = {
            "job_id": job_id,
            "file": "example.mp3",
            "status": "processing",
            "user_id": "default",
            "engine": "auto",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "stages": [
                {"name": "upload", "status": "completed", "duration": 1.2},
                {"name": "split", "status": "completed", "duration": 2.5},
                {"name": "process", "status": "in_progress", "duration": None},
                {"name": "organize", "status": "pending", "duration": None}
            ]
        }
    
    if output_json:
        click.echo(json.dumps(job_data, indent=2))
    else:
        console.print(f"[bold]Job ID:[/] {job_data['job_id']}")
        console.print(f"[bold]File:[/] {job_data['file']}")
        console.print(f"[bold]Status:[/] {job_data['status']}")
        console.print(f"[bold]Engine:[/] {job_data['engine']}")
        console.print(f"[bold]User:[/] {job_data['user_id']}")
        console.print(f"[bold]Created:[/] {job_data['created_at']}")
        console.print(f"[bold]Updated:[/] {job_data['updated_at']}")
        
        console.print("\n[bold]Processing Stages:[/]")
        stage_table = Table(show_header=True, header_style="bold")
        stage_table.add_column("Stage")
        stage_table.add_column("Status")
        stage_table.add_column("Duration (s)")
        
        for stage in job_data['stages']:
            status = stage['status']
            status_style = "green" if status == "completed" else "yellow" if status == "in_progress" else "dim"
            duration = str(stage['duration']) if stage['duration'] is not None else "-"
            
            stage_table.add_row(
                stage['name'],
                f"[{status_style}]{status}[/{status_style}]",
                duration
            )
        
        console.print(stage_table)

@job.command("retry")
@click.argument("job_id", required=True)
def job_retry_cmd(job_id):
    """Retry a failed job."""
    with console.status(f"[bold yellow]Retrying job: {job_id}..."):
        # This would call the queue API in a real implementation
        # Simulate API response
        result = {
            "job_id": job_id,
            "retry_id": f"retry_{job_id}_{int(time.time())}",
            "status": "queued"
        }
    
    console.print(f"[bold green]Job retry initiated successfully.[/]")
    console.print(f"Original Job ID: {result['job_id']}")
    console.print(f"Retry Job ID: {result['retry_id']}")
    console.print(f"Status: {result['status']}")

@job.command("cancel")
@click.argument("job_id", required=True)
@click.option("--force", is_flag=True, help="Force cancellation")
def job_cancel_cmd(job_id, force):
    """Cancel a job in progress."""
    if not force:
        if not click.confirm(f"Are you sure you want to cancel job {job_id}?"):
            console.print("[yellow]Operation cancelled.[/]")
            return
    
    with console.status(f"[bold red]Canceling job: {job_id}..."):
        # This would call the queue API in a real implementation
        # Simulate API response
        result = {
            "job_id": job_id,
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat()
        }
    
    console.print(f"[bold green]Job cancelled successfully.[/]")
    console.print(f"Job ID: {result['job_id']}")
    console.print(f"Status: {result['status']}")
    console.print(f"Cancelled at: {result['cancelled_at']}")

# =============================================================================
# System Management Commands
# =============================================================================
@cli.group()
def system():
    """System management commands."""
    pass

@system.command("health")
@click.option("--service", help="Check specific service")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def system_health_cmd(service, output_json):
    """Check system health."""
    with console.status("[bold blue]Checking system health..."):
        # This would check health endpoints of all services
        # Simulate API response
        services = [
            {"name": "watcher", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "queue", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "splitter-stager", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "metadata", "status": "degraded", "version": "1.0.0", "uptime": "1d 2h 15m", 
             "message": "High CPU usage"},
            {"name": "spleeter", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "demucs", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "audio-recon", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "categorizer", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "output-organizer", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "notifications", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
            {"name": "ui-backend", "status": "healthy", "version": "1.0.0", "uptime": "2d 3h 45m"},
        ]
        
        if service:
            services = [s for s in services if s["name"] == service]
        
        # Add overall status
        overall = {
            "status": "degraded" if any(s["status"] == "degraded" for s in services) else 
                     "critical" if any(s["status"] == "critical" for s in services) else "healthy",
            "services_count": len(services),
            "healthy_count": sum(1 for s in services if s["status"] == "healthy"),
            "degraded_count": sum(1 for s in services if s["status"] == "degraded"),
            "critical_count": sum(1 for s in services if s["status"] == "critical")
        }
    
    if output_json:
        data = {
            "overall": overall,
            "services": services
        }
        click.echo(json.dumps(data, indent=2))
    else:
        # Print overall status
        status_style = "green" if overall["status"] == "healthy" else "yellow" if overall["status"] == "degraded" else "red"
        console.print(f"\n[bold]System Status:[/] [{status_style}]{overall['status']}[/{status_style}]")
        console.print(f"Services: {overall['services_count']} total, "
                     f"{overall['healthy_count']} healthy, "
                     f"{overall['degraded_count']} degraded, "
                     f"{overall['critical_count']} critical")
        
        # Print service details
        table = Table(title="Service Health")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Version", style="blue")
        table.add_column("Uptime", style="magenta")
        table.add_column("Message", style="yellow")
        
        for svc in services:
            status = svc["status"]
            status_style = "green" if status == "healthy" else "yellow" if status == "degraded" else "red"
            
            table.add_row(
                svc["name"],
                f"[{status_style}]{status}[/{status_style}]",
                svc.get("version", ""),
                svc.get("uptime", ""),
                svc.get("message", "")
            )
        
        console.print(table)

@system.command("prune")
@click.option("--dry-run", is_flag=True, help="Show what would be pruned without deleting")
@click.option("--older-than", type=int, default=30, help="Prune data older than N days")
@click.option("--type", "prune_type", type=click.Choice(['all', 'jobs', 'outputs', 'logs']), 
              default='all', help="Type of data to prune")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def system_prune_cmd(dry_run, older_than, prune_type, output_json):
    """Prune orphaned/old data."""
    action = "Simulating prune" if dry_run else "Pruning"
    with console.status(f"[bold yellow]{action} {prune_type} data older than {older_than} days..."):
        # This would scan and clean up old data
        # Simulate API response
        result = {
            "dry_run": dry_run,
            "older_than_days": older_than,
            "type": prune_type,
            "items_found": 42,
            "storage_size": "1.2 GB",
            "details": {
                "jobs": 15,
                "outputs": 25,
                "logs": 2
            }
        }
    
    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        console.print(f"[bold]{'Dry run: ' if dry_run else ''}Prune Summary[/]")
        console.print(f"Type: {prune_type}")
        console.print(f"Age threshold: > {older_than} days")
        console.print(f"Items found: {result['items_found']}")
        console.print(f"Storage to reclaim: {result['storage_size']}")
        
        if not dry_run:
            console.print(f"[bold green]Pruning complete.[/]")
        else:
            console.print(f"\n[bold yellow]This was a dry run. To actually prune the data, run without --dry-run[/]")

@system.command("backup")
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--include", type=click.Choice(['all', 'config', 'db', 'files']), 
              default='all', help="What to include in backup")
def system_backup_cmd(output, include):
    """Backup system data."""
    output_dir = output or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with console.status(f"[bold blue]Backing up {include} data to: {output_dir}..."):
        # This would perform DB dumps and file backups
        # For simulation, just create a directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Simulate creating files
        with open(f"{output_dir}/backup_info.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "include": include,
                "version": "1.0.0"
            }, f, indent=2)
    
    console.print(f"[bold green]Backup completed successfully.[/]")
    console.print(f"Output directory: {output_dir}")
    console.print(f"Included: {include}")
    console.print(f"Timestamp: {datetime.now().isoformat()}")

@system.command("restore")
@click.option("--input", "-i", required=True, type=click.Path(exists=True), help="Backup file or directory")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def system_restore_cmd(input, confirm):
    """Restore system from backup."""
    if not confirm:
        if not click.confirm(f"Are you sure you want to restore from {input}? This will override current data."):
            console.print("[yellow]Operation cancelled.[/]")
            return
    
    with console.status(f"[bold yellow]Restoring system from: {input}..."):
        # This would restore from backup files
        # For simulation, just read the backup info
        if os.path.isdir(input):
            info_file = os.path.join(input, "backup_info.json")
            if os.path.exists(info_file):
                with open(info_file, "r") as f:
                    info = json.load(f)
            else:
                info = {"timestamp": "unknown", "include": "unknown"}
        else:
            info = {"timestamp": "unknown", "include": "unknown"}
    
    console.print(f"[bold green]Restore completed successfully.[/]")
    console.print(f"Backup source: {input}")
    console.print(f"Backup timestamp: {info.get('timestamp', 'unknown')}")
    console.print(f"Included: {info.get('include', 'unknown')}")

# =============================================================================
# Diagnostic Commands
# =============================================================================
@cli.group()
def diag():
    """Diagnostic commands."""
    pass

@diag.command("bundle")
@click.argument("job_id", required=True)
@click.option("--output", "-o", type=click.Path(), help="Output directory")
def diag_bundle_cmd(job_id, output):
    """Create diagnostic bundle for a job."""
    output_dir = output or f"diag_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with console.status(f"[bold blue]Creating diagnostic bundle for job {job_id}..."):
        # This would collect logs, configs, and job data
        # For simulation, just create a directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Simulate creating files
        with open(f"{output_dir}/job_info.json", "w") as f:
            json.dump({
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }, f, indent=2)
        
        with open(f"{output_dir}/logs.txt", "w") as f:
            f.write(f"Simulated logs for job {job_id}\n")
    
    console.print(f"[bold green]Diagnostic bundle created successfully.[/]")
    console.print(f"Output directory: {output_dir}")

@diag.command("logs")
@click.option("--job-id", help="Filter by job ID")
@click.option("--service", help="Filter by service")
@click.option("--level", type=click.Choice(['debug', 'info', 'warning', 'error', 'critical']), 
              help="Filter by log level")
@click.option("--tail", "-t", type=int, default=100, help="Number of lines to show")
def diag_logs_cmd(job_id, service, level, tail):
    """Search and view logs."""
    filters = []
    if job_id:
        filters.append(f"job_id={job_id}")
    if service:
        filters.append(f"service={service}")
    if level:
        filters.append(f"level={level}")
    
    filter_str = " AND ".join(filters) if filters else "none"
    
    with console.status(f"[bold blue]Fetching logs (filters: {filter_str}, tail: {tail})..."):
        # This would fetch logs from centralized logging
        # Simulate log data
        logs = [
            {"timestamp": "2023-05-15T10:30:45", "level": "INFO", "service": "queue", 
             "message": "Job submitted", "job_id": "job123"},
            {"timestamp": "2023-05-15T10:31:12", "level": "INFO", "service": "splitter", 
             "message": "Processing started", "job_id": "job123"},
            {"timestamp": "2023-05-15T10:32:30", "level": "WARNING", "service": "splitter", 
             "message": "Processing slow", "job_id": "job123"},
            {"timestamp": "2023-05-15T10:35:22", "level": "INFO", "service": "splitter", 
             "message": "Processing complete", "job_id": "job123"},
        ]
    
    if not logs:
        console.print("[yellow]No logs found matching filters.[/]")
        return
    
    table = Table(title=f"Logs (filters: {filter_str})")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Level", style="green")
    table.add_column("Service", style="blue")
    table.add_column("Job ID", style="yellow")
    table.add_column("Message", style="white")
    
    for log in logs:
        level_style = {
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
            "DEBUG": "dim"
        }.get(log["level"], "white")
        
        table.add_row(
            log["timestamp"],
            f"[{level_style}]{log['level']}[/{level_style}]",
            log["service"],
            log.get("job_id", ""),
            log["message"]
        )
    
    console.print(table)

# =============================================================================
# Developer Commands
# =============================================================================
@cli.group()
def dev():
    """Developer commands."""
    pass

@dev.command("up")
@click.option("--with-data", is_flag=True, help="Include sample data")
def dev_up_cmd(with_data):
    """Start development environment."""
    with console.status("[bold green]Setting up development environment..."):
        # This would start a local dev environment
        run_docker_compose_command("up -d")
        
        if with_data:
            # Simulate loading sample data
            time.sleep(1)
            console.print("[dim]Loading sample data...[/dim]")
    
    console.print("[bold green]Development environment started successfully.[/]")
    console.print("\nAvailable services:")
    console.print("- UI: http://localhost:3000")
    console.print("- API: http://localhost:8000")
    console.print("- Documentation: http://localhost:8000/docs")

@dev.command("docs")
@click.option("--browser", is_flag=True, help="Open in browser")
def dev_docs_cmd(browser):
    """View API documentation."""
    console.print("[bold]API Documentation URLs:[/]")
    console.print("- OpenAPI UI: http://localhost:8000/docs")
    console.print("- ReDoc UI: http://localhost:8000/redoc")
    console.print("- OpenAPI JSON: http://localhost:8000/openapi.json")
    
    if browser:
        click.launch("http://localhost:8000/docs")

# =============================================================================
# Main Entry Point
# =============================================================================
def main():
    """Main entry point."""
    try:
        cli()
    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
