# MemoryOS Development Environment Verification Script
# ==================================================

param(
    [switch]$InstallTools,
    [switch]$Verbose
)

Write-Host "🔍 MemoryOS Development Environment Check" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

function Test-Command {
    param([string]$Command, [string]$Name)
    try {
        $result = Invoke-Expression "$Command 2>&1"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $Name`: Available" -ForegroundColor Green
            if ($Verbose) { Write-Host "   $result" -ForegroundColor Gray }
            return $true
        } else {
            Write-Host "❌ $Name`: Error" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ $Name`: Not found" -ForegroundColor Red
        return $false
    }
}

function Test-DockerStatus {
    Write-Host "🐳 Docker Status:" -ForegroundColor Yellow

    # Check Docker version
    $dockerOk = Test-Command "docker --version" "Docker Client"

    if ($dockerOk) {
        # Check Docker daemon
        try {
            $dockerInfo = docker info --format "json" 2>$null | ConvertFrom-Json
            Write-Host "✅ Docker Engine: Running" -ForegroundColor Green
            Write-Host "   Server Version: $($dockerInfo.ServerVersion)" -ForegroundColor Gray
            Write-Host "   Containers: $($dockerInfo.Containers)" -ForegroundColor Gray
            Write-Host "   Images: $($dockerInfo.Images)" -ForegroundColor Gray
            return $true
        } catch {
            Write-Host "❌ Docker Engine: Not running" -ForegroundColor Red
            Write-Host "   Start Docker Desktop and try again" -ForegroundColor Yellow
            return $false
        }
    }
    return $false
}

function Test-KubernetesStatus {
    Write-Host "`n☸️  Kubernetes Status:" -ForegroundColor Yellow

    # Check kubectl
    $kubectlOk = Test-Command "kubectl version --client=true" "kubectl"

    if ($kubectlOk) {
        # Check cluster connectivity
        try {
            $clusterInfo = kubectl cluster-info 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Kubernetes Cluster: Connected" -ForegroundColor Green

                # Check nodes
                $nodes = kubectl get nodes --no-headers 2>$null
                if ($nodes) {
                    Write-Host "   Nodes: $(($nodes -split "`n").Count)" -ForegroundColor Gray
                    if ($Verbose) {
                        kubectl get nodes 2>$null | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
                    }
                }

                # Check namespaces
                $namespaces = kubectl get namespaces --no-headers 2>$null
                if ($namespaces) {
                    Write-Host "   Namespaces: $(($namespaces -split "`n").Count)" -ForegroundColor Gray
                }

                return $true
            } else {
                Write-Host "❌ Kubernetes Cluster: Not accessible" -ForegroundColor Red
                Write-Host "   Enable Kubernetes in Docker Desktop" -ForegroundColor Yellow
                return $false
            }
        } catch {
            Write-Host "❌ Kubernetes Cluster: Connection failed" -ForegroundColor Red
            return $false
        }
    }
    return $false
}

function Test-DevelopmentTools {
    Write-Host "`n🛠️  Development Tools:" -ForegroundColor Yellow

    $tools = @{
        "Skaffold" = "skaffold version"
        "Helm" = "helm version --short"
        "Python" = "python --version"
        "Git" = "git --version"
    }

    $results = @{}
    foreach ($tool in $tools.Keys) {
        $results[$tool] = Test-Command $tools[$tool] $tool
    }

    return $results
}

function Install-MissingTools {
    Write-Host "`n📦 Installing Missing Tools:" -ForegroundColor Yellow

    # Install Skaffold
    try {
        Write-Host "Installing Skaffold..." -ForegroundColor Cyan
        winget install --id=skaffold.skaffold -e --silent
        Write-Host "✅ Skaffold installed" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to install Skaffold" -ForegroundColor Red
    }

    # Install Helm
    try {
        Write-Host "Installing Helm..." -ForegroundColor Cyan
        winget install --id=Helm.Helm -e --silent
        Write-Host "✅ Helm installed" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to install Helm" -ForegroundColor Red
    }
}

function Test-MemoryOSSetup {
    Write-Host "`n🧠 MemoryOS Setup:" -ForegroundColor Yellow

    # Check if we're in the right directory
    if (Test-Path "deployments/local/setup-local-k8s.ps1") {
        Write-Host "✅ Setup script: Found" -ForegroundColor Green
    } else {
        Write-Host "❌ Setup script: Not found" -ForegroundColor Red
        Write-Host "   Run from MemoryOS root directory" -ForegroundColor Yellow
        return $false
    }

    # Check configuration files
    $configFiles = @(
        "deployments/local/k8s/memoryos-deployment.yaml",
        "deployments/local/k8s/postgres-deployment.yaml",
        "deployments/local/k8s/redis-deployment.yaml",
        "deployments/local/k8s/mock-services-deployment.yaml",
        "deployments/local/skaffold.yaml"
    )

    $missingFiles = @()
    foreach ($file in $configFiles) {
        if (Test-Path $file) {
            if ($Verbose) { Write-Host "   ✅ $file" -ForegroundColor Gray }
        } else {
            Write-Host "   ❌ $file" -ForegroundColor Red
            $missingFiles += $file
        }
    }

    if ($missingFiles.Count -eq 0) {
        Write-Host "✅ Configuration files: All present" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ Configuration files: $($missingFiles.Count) missing" -ForegroundColor Red
        return $false
    }
}

# Main execution
try {
    $dockerOk = Test-DockerStatus
    $kubernetesOk = Test-KubernetesStatus
    $toolsResults = Test-DevelopmentTools
    $setupOk = Test-MemoryOSSetup

    Write-Host "`n📊 SUMMARY:" -ForegroundColor Cyan
    Write-Host "==========" -ForegroundColor Cyan

    if ($dockerOk) {
        Write-Host "✅ Docker: Ready" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker: Issues detected" -ForegroundColor Red
    }

    if ($kubernetesOk) {
        Write-Host "✅ Kubernetes: Ready" -ForegroundColor Green
    } else {
        Write-Host "❌ Kubernetes: Not ready" -ForegroundColor Red
    }

    $toolsReady = $true
    foreach ($tool in $toolsResults.Keys) {
        if (-not $toolsResults[$tool]) {
            $toolsReady = $false
            break
        }
    }

    if ($toolsReady) {
        Write-Host "✅ Development Tools: Ready" -ForegroundColor Green
    } else {
        Write-Host "❌ Development Tools: Missing tools detected" -ForegroundColor Red
    }

    if ($setupOk) {
        Write-Host "✅ MemoryOS Setup: Ready" -ForegroundColor Green
    } else {
        Write-Host "❌ MemoryOS Setup: Issues detected" -ForegroundColor Red
    }

    Write-Host ""

    if ($dockerOk -and $kubernetesOk -and $toolsReady -and $setupOk) {
        Write-Host "🎉 ENVIRONMENT READY!" -ForegroundColor Green
        Write-Host "You can now run: .\deployments\local\setup-local-k8s.ps1" -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  SETUP REQUIRED" -ForegroundColor Yellow

        if (-not $dockerOk) {
            Write-Host "• Start Docker Desktop" -ForegroundColor Yellow
        }

        if (-not $kubernetesOk) {
            Write-Host "• Enable Kubernetes in Docker Desktop" -ForegroundColor Yellow
        }

        if (-not $toolsReady) {
            Write-Host "• Install missing development tools" -ForegroundColor Yellow
            if ($InstallTools) {
                Install-MissingTools
            } else {
                Write-Host "  Run with -InstallTools to auto-install" -ForegroundColor Gray
            }
        }

        if (-not $setupOk) {
            Write-Host "• Ensure you're in the MemoryOS root directory" -ForegroundColor Yellow
        }
    }

} catch {
    Write-Host "❌ Error during verification: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Run .\deployments\local\verify-environment.ps1 -Verbose for detailed output" -ForegroundColor Gray
Write-Host "Run .\deployments\local\verify-environment.ps1 -InstallTools to auto-install missing tools" -ForegroundColor Gray
