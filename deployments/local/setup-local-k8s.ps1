# MemoryOS Local Kubernetes Setup Script
# =====================================
# Sub-issue #5.1: Configure local Kubernetes cluster

param(
    [switch]$Clean,
    [switch]$Monitoring,
    [switch]$Verbose
)

# Configuration
$NAMESPACE = "memoryos-dev"
$KUBECTL = "kubectl"

Write-Host "🚀 MemoryOS Local Kubernetes Setup" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Helper Functions
function Write-Status {
    param([string]$Message, [string]$Color = "Yellow")
    Write-Host "⚡ $Message" -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Test-KubernetesConnection {
    try {
        $nodes = & $KUBECTL get nodes --no-headers 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Kubernetes cluster is accessible"
            return $true
        }
    }
    catch {
        Write-Error "Failed to connect to Kubernetes cluster"
        return $false
    }
    return $false
}

function Install-IngressController {
    Write-Status "Installing NGINX Ingress Controller..."

    # Check if ingress controller already exists
    $existing = & $KUBECTL get deployment -n ingress-nginx ingress-nginx-controller 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "NGINX Ingress Controller already installed"
        return
    }

    # Install NGINX Ingress Controller
    & $KUBECTL apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

    if ($LASTEXITCODE -eq 0) {
        Write-Success "NGINX Ingress Controller installed"

        # Wait for ingress controller to be ready
        Write-Status "Waiting for ingress controller to be ready..."
        & $KUBECTL wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=300s

        if ($LASTEXITCODE -eq 0) {
            Write-Success "NGINX Ingress Controller is ready"
        } else {
            Write-Error "Timeout waiting for ingress controller"
        }
    } else {
        Write-Error "Failed to install NGINX Ingress Controller"
    }
}

function Create-Namespace {
    Write-Status "Creating namespace: $NAMESPACE"

    $existing = & $KUBECTL get namespace $NAMESPACE 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Namespace $NAMESPACE already exists"
    } else {
        & $KUBECTL create namespace $NAMESPACE
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Namespace $NAMESPACE created"
        } else {
            Write-Error "Failed to create namespace $NAMESPACE"
            exit 1
        }
    }
}

function Deploy-Dependencies {
    Write-Status "Deploying dependencies..."

    # Deploy PostgreSQL
    Write-Status "Deploying PostgreSQL..."
    & $KUBECTL apply -f k8s/postgres-deployment.yaml -n $NAMESPACE

    # Deploy Redis
    Write-Status "Deploying Redis..."
    & $KUBECTL apply -f k8s/redis-deployment.yaml -n $NAMESPACE

    # Deploy MinIO
    Write-Status "Deploying MinIO..."
    & $KUBECTL apply -f k8s/minio-deployment.yaml -n $NAMESPACE

    Write-Success "Dependencies deployed"
}

function Deploy-MemoryOS {
    Write-Status "Deploying MemoryOS application..."

    # Apply ConfigMap
    & $KUBECTL apply -f k8s/memoryos-configmap.yaml -n $NAMESPACE

    # Apply Secrets
    & $KUBECTL apply -f k8s/memoryos-secrets.yaml -n $NAMESPACE

    # Apply Deployment
    & $KUBECTL apply -f k8s/memoryos-deployment.yaml -n $NAMESPACE

    # Apply Service
    & $KUBECTL apply -f k8s/memoryos-service.yaml -n $NAMESPACE

    # Apply Ingress
    & $KUBECTL apply -f k8s/ingress.yaml -n $NAMESPACE

    Write-Success "MemoryOS application deployed"
}

function Deploy-Monitoring {
    if (-not $Monitoring) {
        Write-Status "Skipping monitoring stack (use -Monitoring to enable)"
        return
    }

    Write-Status "Deploying monitoring stack..."

    # Deploy Prometheus
    & $KUBECTL apply -f k8s/monitoring/prometheus-deployment.yaml -n $NAMESPACE

    # Deploy Grafana
    & $KUBECTL apply -f k8s/monitoring/grafana-deployment.yaml -n $NAMESPACE

    # Deploy Jaeger
    & $KUBECTL apply -f k8s/monitoring/jaeger-deployment.yaml -n $NAMESPACE

    Write-Success "Monitoring stack deployed"
}

function Wait-ForDeployments {
    Write-Status "Waiting for deployments to be ready..."

    $deployments = @("postgres", "redis", "minio", "memoryos-api")

    foreach ($deployment in $deployments) {
        Write-Status "Waiting for $deployment..."
        & $KUBECTL wait --for=condition=available --timeout=300s deployment/$deployment -n $NAMESPACE

        if ($LASTEXITCODE -eq 0) {
            Write-Success "$deployment is ready"
        } else {
            Write-Error "$deployment failed to become ready"
        }
    }
}

function Show-AccessInfo {
    Write-Host ""
    Write-Host "🌐 Access Information" -ForegroundColor Cyan
    Write-Host "=====================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "MemoryOS API:" -ForegroundColor White
    Write-Host "  - URL: http://localhost:8080" -ForegroundColor Gray
    Write-Host "  - Health: http://localhost:8080/health" -ForegroundColor Gray
    Write-Host "  - Docs: http://localhost:8080/docs" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Port Forward Commands:" -ForegroundColor White
    Write-Host "  kubectl port-forward -n $NAMESPACE service/memoryos-api 8080:80" -ForegroundColor Gray
    Write-Host "  kubectl port-forward -n $NAMESPACE service/postgres 5432:5432" -ForegroundColor Gray
    Write-Host "  kubectl port-forward -n $NAMESPACE service/redis 6379:6379" -ForegroundColor Gray
    Write-Host "  kubectl port-forward -n $NAMESPACE service/minio 9000:9000" -ForegroundColor Gray

    if ($Monitoring) {
        Write-Host ""
        Write-Host "Monitoring:" -ForegroundColor White
        Write-Host "  kubectl port-forward -n $NAMESPACE service/prometheus 9090:9090" -ForegroundColor Gray
        Write-Host "  kubectl port-forward -n $NAMESPACE service/grafana 3000:3000" -ForegroundColor Gray
        Write-Host "  kubectl port-forward -n $NAMESPACE service/jaeger 16686:16686" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor White
    Write-Host "  kubectl get pods -n $NAMESPACE" -ForegroundColor Gray
    Write-Host "  kubectl logs -f deployment/memoryos-api -n $NAMESPACE" -ForegroundColor Gray
    Write-Host "  kubectl describe pod <pod-name> -n $NAMESPACE" -ForegroundColor Gray
    Write-Host ""
}

function Clean-Environment {
    Write-Status "Cleaning up local environment..."

    & $KUBECTL delete namespace $NAMESPACE --ignore-not-found=true

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Environment cleaned up"
    } else {
        Write-Error "Failed to clean up environment"
    }
}

# Main execution
if (-not (Test-KubernetesConnection)) {
    Write-Error "Please ensure Docker Desktop with Kubernetes is running"
    Write-Host "Enable Kubernetes in Docker Desktop Settings → Kubernetes → Enable Kubernetes" -ForegroundColor Yellow
    exit 1
}

if ($Clean) {
    Clean-Environment
    exit 0
}

try {
    Install-IngressController
    Create-Namespace
    Deploy-Dependencies
    Deploy-MemoryOS
    Deploy-Monitoring
    Wait-ForDeployments
    Show-AccessInfo

    Write-Host ""
    Write-Success "🎉 MemoryOS local environment is ready!"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Port forward services: kubectl port-forward -n $NAMESPACE service/memoryos-api 8080:80" -ForegroundColor Gray
    Write-Host "2. Visit http://localhost:8080/docs for API documentation" -ForegroundColor Gray
    Write-Host "3. Run tests: cd ../../ && python -m pytest tests/" -ForegroundColor Gray
    Write-Host ""
    # Deploy mock services
    Write-Host "🎭 Deploying Mock Services..." -ForegroundColor Cyan
    kubectl apply -f k8s/mock-services-deployment.yaml

    # Wait for mock services to be ready
    Write-Host "Waiting for mock services to be ready..." -ForegroundColor Yellow
    kubectl wait --for=condition=ready pod -l app=mock-services -n memoryos-dev --timeout=120s
}
catch {
    Write-Error "Setup failed: $($_.Exception.Message)"
    exit 1
}
