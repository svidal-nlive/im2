#!/bin/bash
# pipelinectl shell completion script
# Add to your ~/.bashrc:
# source /path/to/pipelinectl_completion.sh

_pipelinectl_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Top level commands
    local commands="pipeline job system diag dev"
    
    # Pipeline subcommands
    local pipeline_commands="up down status logs pause resume"
    
    # Job subcommands
    local job_commands="submit list status retry cancel"
    
    # System subcommands
    local system_commands="health prune backup restore"
    
    # Diag subcommands
    local diag_commands="bundle logs"
    
    # Dev subcommands
    local dev_commands="up docs"
    
    # Options for specific commands
    local job_submit_opts="--file --engine --user --metadata --json"
    local job_list_opts="--status --user --limit --json"
    local job_status_opts="--json"
    local job_retry_opts=""
    local job_cancel_opts="--force"
    
    local pipeline_up_opts="--detach --build"
    local pipeline_down_opts="--volumes"
    local pipeline_status_opts="--json"
    local pipeline_logs_opts="--follow --tail"
    local pipeline_pause_opts="--confirm"
    local pipeline_resume_opts=""
    
    local system_health_opts="--service --json"
    local system_prune_opts="--dry-run --older-than --type --json"
    local system_backup_opts="--output --include"
    local system_restore_opts="--input --confirm"
    
    local diag_bundle_opts="--output"
    local diag_logs_opts="--job-id --service --level --tail"
    
    local dev_up_opts="--with-data"
    local dev_docs_opts="--browser"
    
    # Handle completion for main commands
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
        return 0
    fi
    
    # Handle completion for subcommands
    if [[ ${COMP_CWORD} -eq 2 ]]; then
        case "${prev}" in
            pipeline)
                COMPREPLY=( $(compgen -W "${pipeline_commands}" -- ${cur}) )
                ;;
            job)
                COMPREPLY=( $(compgen -W "${job_commands}" -- ${cur}) )
                ;;
            system)
                COMPREPLY=( $(compgen -W "${system_commands}" -- ${cur}) )
                ;;
            diag)
                COMPREPLY=( $(compgen -W "${diag_commands}" -- ${cur}) )
                ;;
            dev)
                COMPREPLY=( $(compgen -W "${dev_commands}" -- ${cur}) )
                ;;
            *)
                ;;
        esac
        return 0
    fi
    
    # Handle completion for options
    if [[ ${COMP_CWORD} -ge 3 ]]; then
        command="${COMP_WORDS[1]}"
        subcommand="${COMP_WORDS[2]}"
        
        case "${command} ${subcommand}" in
            "pipeline up")
                COMPREPLY=( $(compgen -W "${pipeline_up_opts}" -- ${cur}) )
                ;;
            "pipeline down")
                COMPREPLY=( $(compgen -W "${pipeline_down_opts}" -- ${cur}) )
                ;;
            "pipeline status")
                COMPREPLY=( $(compgen -W "${pipeline_status_opts}" -- ${cur}) )
                ;;
            "pipeline logs")
                COMPREPLY=( $(compgen -W "${pipeline_logs_opts}" -- ${cur}) )
                ;;
            "pipeline pause")
                COMPREPLY=( $(compgen -W "${pipeline_pause_opts}" -- ${cur}) )
                ;;
            "pipeline resume")
                COMPREPLY=( $(compgen -W "${pipeline_resume_opts}" -- ${cur}) )
                ;;
            "job submit")
                COMPREPLY=( $(compgen -W "${job_submit_opts}" -- ${cur}) )
                ;;
            "job list")
                COMPREPLY=( $(compgen -W "${job_list_opts}" -- ${cur}) )
                ;;
            "job status")
                COMPREPLY=( $(compgen -W "${job_status_opts}" -- ${cur}) )
                ;;
            "job retry")
                COMPREPLY=( $(compgen -W "${job_retry_opts}" -- ${cur}) )
                ;;
            "job cancel")
                COMPREPLY=( $(compgen -W "${job_cancel_opts}" -- ${cur}) )
                ;;
            "system health")
                COMPREPLY=( $(compgen -W "${system_health_opts}" -- ${cur}) )
                ;;
            "system prune")
                COMPREPLY=( $(compgen -W "${system_prune_opts}" -- ${cur}) )
                ;;
            "system backup")
                COMPREPLY=( $(compgen -W "${system_backup_opts}" -- ${cur}) )
                ;;
            "system restore")
                COMPREPLY=( $(compgen -W "${system_restore_opts}" -- ${cur}) )
                ;;
            "diag bundle")
                COMPREPLY=( $(compgen -W "${diag_bundle_opts}" -- ${cur}) )
                ;;
            "diag logs")
                COMPREPLY=( $(compgen -W "${diag_logs_opts}" -- ${cur}) )
                ;;
            "dev up")
                COMPREPLY=( $(compgen -W "${dev_up_opts}" -- ${cur}) )
                ;;
            "dev docs")
                COMPREPLY=( $(compgen -W "${dev_docs_opts}" -- ${cur}) )
                ;;
            *)
                ;;
        esac
        return 0
    fi
}

complete -F _pipelinectl_completion pipelinectl
