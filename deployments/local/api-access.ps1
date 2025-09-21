# MemoryOS API Access Helper Script
# =================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("service", "pod1", "pod2", "ingress", "status")]
    [string]$AccessMethod,

    [int]$Port = 8080
)

$NAMESPACE = "memoryos-dev"

function Show-Status {
    Write-Host "🔍 MemoryOS API Status Check" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan

    # Check pods
    Write-Host "`n📦 Pods:" -ForegroundColor Yellow
    kubectl get pods -n $NAMESPACE -l app=memoryos-api

    # Check service
    Write-Host "`n🔗 Service:" -ForegroundColor Yellow
    kubectl get service memoryos-api -n $NAMESPACE

    # Check ingress
    Write-Host "`n🌐 Ingress:" -ForegroundColor Yellow
    kubectl get ingress -n $NAMESPACE

    # Check current port forwarding
    Write-Host "`n🔌 Active Port Forwards:" -ForegroundColor Yellow
    Get-Process -Name "kubectl" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*port-forward*" }
}

function Start-ServiceAccess {
    param([int]$LocalPort)

    Write-Host "🚀 Starting Service Access on port $LocalPort" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "Load balances between all healthy pods" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Access URLs:" -ForegroundColor Cyan
    Write-Host "  Health: http://localhost:$LocalPort/health" -ForegroundColor White
    Write-Host "  Docs:   http://localhost:$LocalPort/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "Press Ctrl+C to stop port forwarding" -ForegroundColor Yellow
    Write-Host ""

    kubectl port-forward -n $NAMESPACE service/memoryos-api "$LocalPort:80"
}

function Start-PodAccess {
    param([string]$PodName, [int]$LocalPort)

    Write-Host "🎯 Starting Direct Pod Access: $PodName" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "Connects directly to specific pod instance" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Access URLs:" -ForegroundColor Cyan
    Write-Host "  Health: http://localhost:$LocalPort/health" -ForegroundColor White
    Write-Host "  Docs:   http://localhost:$LocalPort/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "Press Ctrl+C to stop port forwarding" -ForegroundColor Yellow
    Write-Host ""

    kubectl port-forward -n $NAMESPACE pod/$PodName "$LocalPort:8000"
}

function Test-IngressAccess {
    Write-Host "🌐 Testing Ingress Access" -ForegroundColor Green
    Write-Host "==========================" -ForegroundColor Green

    # Check if ingress controller is running
    $ingressPods = kubectl get pods -n ingress-nginx --no-headers 2>$null
    if ($LASTEXITCODE -eq 0 -and $ingressPods) {
        Write-Host "✅ NGINX Ingress Controller: Running" -ForegroundColor Green

        # Test direct localhost access
        try {
            $response = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing -TimeoutSec 5
            Write-Host "✅ Ingress Access: Working" -ForegroundColor Green
            Write-Host "   URL: http://localhost" -ForegroundColor White
            Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Gray
        }
        catch {
            Write-Host "❌ Ingress Access: Not working" -ForegroundColor Red
            Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Gray
            Write-Host "   Try: Check ingress configuration" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "❌ NGINX Ingress Controller: Not running" -ForegroundColor Red
    }
}

# Main execution
try {
    switch ($AccessMethod) {
        "status" {
            Show-Status
        }
        "service" {
            Start-ServiceAccess -LocalPort $Port
        }
        "pod1" {
            $pods = kubectl get pods -n $NAMESPACE -l app=memoryos-api --no-headers -o custom-columns=":metadata.name"
            $podArray = $pods -split "`n" | Where-Object { $_ -ne "" }
            if ($podArray.Count -gt 0) {
                Start-PodAccess -PodName $podArray[0] -LocalPort $Port
            } else {
                Write-Host "❌ No pods found" -ForegroundColor Red
            }
        }
        "pod2" {
            $pods = kubectl get pods -n $NAMESPACE -l app=memoryos-api --no-headers -o custom-columns=":metadata.name"
            $podArray = $pods -split "`n" | Where-Object { $_ -ne "" }
            if ($podArray.Count -gt 1) {
                Start-PodAccess -PodName $podArray[1] -LocalPort $Port
            } else {
                Write-Host "❌ Second pod not found" -ForegroundColor Red
            }
        }
        "ingress" {
            Test-IngressAccess
        }
    }
}
catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Usage help
if ($AccessMethod -eq "status") {
    Write-Host "`n💡 Usage Examples:" -ForegroundColor Cyan
    Write-Host "   .\api-access.ps1 service      # Access via service (load balanced)" -ForegroundColor White
    Write-Host "   .\api-access.ps1 pod1         # Access first pod directly" -ForegroundColor White
    Write-Host "   .\api-access.ps1 pod2         # Access second pod directly" -ForegroundColor White
    Write-Host "   .\api-access.ps1 ingress      # Test ingress access" -ForegroundColor White
    Write-Host "   .\api-access.ps1 status       # Show this status" -ForegroundColor White
    Write-Host ""
    Write-Host "   .\api-access.ps1 service -Port 8081  # Use custom port" -ForegroundColor Gray
}
