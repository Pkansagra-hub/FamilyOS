# MemoryOS Local Kubernetes Cleanup Script
# =========================================

param(
    [switch]$All,
    [switch]$KeepData,
    [switch]$Verbose
)

$NAMESPACE = "memoryos-dev"
$KUBECTL = "kubectl"

Write-Host "🧹 MemoryOS Local Kubernetes Cleanup" -ForegroundColor Red
Write-Host "====================================" -ForegroundColor Red

function Write-Status {
    param([string]$Message)
    Write-Host "⚡ $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Clean-Namespace {
    Write-Status "Removing namespace: $NAMESPACE"

    $existing = & $KUBECTL get namespace $NAMESPACE 2>$null
    if ($LASTEXITCODE -eq 0) {
        & $KUBECTL delete namespace $NAMESPACE
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Namespace $NAMESPACE removed"
        } else {
            Write-Host "❌ Failed to remove namespace $NAMESPACE" -ForegroundColor Red
        }
    } else {
        Write-Success "Namespace $NAMESPACE does not exist"
    }
}

function Clean-PersistentData {
    if ($KeepData) {
        Write-Status "Keeping persistent data (use without -KeepData to remove)"
        return
    }

    Write-Status "Removing persistent volumes..."

    # Get PVs that were bound to PVCs in our namespace
    $pvs = & $KUBECTL get pv -o jsonpath='{.items[?(@.spec.claimRef.namespace=="' + $NAMESPACE + '")].metadata.name}' 2>$null

    if ($pvs) {
        foreach ($pv in $pvs.Split(' ')) {
            if ($pv) {
                Write-Status "Removing persistent volume: $pv"
                & $KUBECTL delete pv $pv --ignore-not-found=true
            }
        }
        Write-Success "Persistent volumes cleaned up"
    } else {
        Write-Success "No persistent volumes to clean up"
    }
}

function Clean-IngressController {
    if (-not $All) {
        Write-Status "Keeping NGINX Ingress Controller (use -All to remove)"
        return
    }

    Write-Status "Removing NGINX Ingress Controller..."

    & $KUBECTL delete namespace ingress-nginx --ignore-not-found=true

    if ($LASTEXITCODE -eq 0) {
        Write-Success "NGINX Ingress Controller removed"
    } else {
        Write-Host "❌ Failed to remove NGINX Ingress Controller" -ForegroundColor Red
    }
}

function Show-CleanupStatus {
    Write-Host ""
    Write-Host "🔍 Cleanup Status" -ForegroundColor Cyan
    Write-Host "=================" -ForegroundColor Cyan
    Write-Host ""

    # Check if namespace still exists
    $namespaceExists = & $KUBECTL get namespace $NAMESPACE 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "❌ Namespace $NAMESPACE still exists" -ForegroundColor Red

        # Show remaining resources
        Write-Host ""
        Write-Host "Remaining resources:" -ForegroundColor Yellow
        & $KUBECTL get all -n $NAMESPACE
    } else {
        Write-Host "✅ Namespace $NAMESPACE successfully removed" -ForegroundColor Green
    }

    # Check ingress controller
    $ingressExists = & $KUBECTL get namespace ingress-nginx 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "ℹ️  NGINX Ingress Controller still installed" -ForegroundColor Blue
    } else {
        Write-Host "✅ NGINX Ingress Controller removed" -ForegroundColor Green
    }

    Write-Host ""
}

try {
    Clean-Namespace
    Clean-PersistentData
    Clean-IngressController

    # Wait a moment for cleanup to complete
    Start-Sleep -Seconds 5

    Show-CleanupStatus

    Write-Host ""
    Write-Success "🎉 Cleanup completed!"
    Write-Host ""
    Write-Host "To restart the environment:" -ForegroundColor Cyan
    Write-Host "  ./setup-local-k8s.ps1" -ForegroundColor Gray
    Write-Host ""
}
catch {
    Write-Host "❌ Cleanup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
