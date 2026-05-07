# PowerShell script to completely reset ChromaDB database

Write-Host "=== ChromaDB Database Reset ===" -ForegroundColor Red
Write-Host "This will PERMANENTLY delete all ChromaDB data!" -ForegroundColor Red
Write-Host ""

$confirm = Read-Host "Are you sure you want to delete ALL ChromaDB data? (yes/no)"

if ($confirm -eq "yes") {
    Write-Host "Proceeding with database deletion..." -ForegroundColor Yellow
    
    # Stop any running ChromaDB processes
    Write-Host "Stopping ChromaDB processes..." -ForegroundColor Cyan
    Get-Process -Name "chroma" -ErrorAction SilentlyContinue | Stop-Process -Force
    
    # Delete the ChromaDB directory
    $chromaPath = ".\chroma_db"
    if (Test-Path $chromaPath) {
        Write-Host "Deleting ChromaDB directory: $chromaPath" -ForegroundColor Cyan
        Remove-Item -Path $chromaPath -Recurse -Force
        Write-Host "✅ ChromaDB directory deleted successfully!" -ForegroundColor Green
    } else {
        Write-Host "ChromaDB directory not found at: $chromaPath" -ForegroundColor Yellow
    }
    
    # Also delete any temporary ChromaDB files
    $tempChroma = ".\chroma_db_temp"
    if (Test-Path $tempChroma) {
        Write-Host "Deleting temporary ChromaDB directory: $tempChroma" -ForegroundColor Cyan
        Remove-Item -Path $tempChroma -Recurse -Force
        Write-Host "✅ Temporary ChromaDB directory deleted!" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "=== Database Reset Complete ===" -ForegroundColor Green
    Write-Host "All ChromaDB data has been permanently deleted." -ForegroundColor Green
    Write-Host "You can now start fresh with a new database." -ForegroundColor Green
    
} else {
    Write-Host "Database reset cancelled." -ForegroundColor Yellow
} 