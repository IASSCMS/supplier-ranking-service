# PowerShell script to run all three services
# Usage: .\run_all_services.ps1

# Define the paths to each service
$authServicePath = "C:\path\to\auth-service"
$rankingServicePath = $PSScriptRoot  # Current directory for ranking service
$productServicePath = "C:\path\to\product-service"

# Function to start a service in a new PowerShell window
function Start-Service {
    param (
        [string]$servicePath,
        [string]$command,
        [string]$windowTitle
    )
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$servicePath'; $command; Read-Host 'Press Enter to exit'" -WindowStyle Normal -WorkingDirectory $servicePath
}

Write-Host "Starting all services..." -ForegroundColor Green

# Start Auth Service (Port 8000)
Write-Host "Starting Auth Service on port 8000..." -ForegroundColor Cyan
Start-Service -servicePath $authServicePath -command "python manage.py runserver 0.0.0.0:8000" -windowTitle "Auth Service"

# Start Supplier Ranking Service (Port 8001)
Write-Host "Starting Supplier Ranking Service on port 8001..." -ForegroundColor Cyan
Start-Service -servicePath $rankingServicePath -command "python run_ranking_service.py" -windowTitle "Ranking Service"

# Start Product Service (Port 8002)
Write-Host "Starting Product Service on port 8002..." -ForegroundColor Cyan
Start-Service -servicePath $productServicePath -command "python manage.py runserver 0.0.0.0:8002" -windowTitle "Product Service"

Write-Host "All services started!" -ForegroundColor Green
Write-Host "Auth Service:           http://localhost:8000" -ForegroundColor Yellow
Write-Host "Supplier Ranking Service: http://localhost:8001" -ForegroundColor Yellow
Write-Host "Product Service:        http://localhost:8002" -ForegroundColor Yellow 