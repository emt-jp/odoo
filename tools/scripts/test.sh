#!/bin/bash

# Odoo Enterprise Features - Test Script
# ======================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Function to build images
build_images() {
    print_status "Building Docker images..."
    docker-compose build
    print_success "Docker images built successfully"
}

# Function to start test database
start_test_db() {
    print_status "Starting test database..."
    docker-compose -f docker-compose.test.yml up -d test_db test_redis
    print_success "Test database started"
}

# Function to wait for database to be ready
wait_for_db() {
    print_status "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.test.yml exec test_db pg_isready -U odoo -d odoo_test > /dev/null 2>&1; then
            print_success "Database is ready"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts - Database not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Database failed to start within expected time"
    exit 1
}

# Function to run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    docker-compose -f docker-compose.test.yml run --rm unit_tests
    print_success "Unit tests completed"
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    docker-compose -f docker-compose.test.yml run --rm integration_tests
    print_success "Integration tests completed"
}

# Function to run end-to-end tests
run_e2e_tests() {
    print_status "Running end-to-end tests..."
    docker-compose -f docker-compose.test.yml run --rm e2e_tests
    print_success "End-to-end tests completed"
}

# Function to run performance tests
run_performance_tests() {
    print_status "Running performance tests..."
    docker-compose -f docker-compose.test.yml run --rm performance_tests
    print_success "Performance tests completed"
}

# Function to run security tests
run_security_tests() {
    print_status "Running security tests..."
    docker-compose -f docker-compose.test.yml run --rm security_tests
    print_success "Security tests completed"
}

# Function to run all tests
run_all_tests() {
    print_status "Running all tests..."
    docker-compose -f docker-compose.test.yml run --rm all_tests
    print_success "All tests completed"
}

# Function to generate coverage report
generate_coverage_report() {
    print_status "Generating coverage report..."
    
    # Check if test results exist
    if [ -d "test_results" ]; then
        print_success "Coverage report generated in test_results/htmlcov/index.html"
        print_status "Coverage XML report: test_results/coverage.xml"
        print_status "JUnit XML report: test_results/junit.xml"
        print_status "HTML report: test_results/report.html"
    else
        print_warning "No test results found. Run tests first."
    fi
}

# Function to clean up test containers
cleanup() {
    print_status "Cleaning up test containers..."
    docker-compose -f docker-compose.test.yml down -v
    print_success "Test containers cleaned up"
}

# Function to show test results
show_results() {
    print_status "Test Results Summary:"
    echo "========================"
    
    if [ -f "test_results/junit.xml" ]; then
        echo "JUnit XML: test_results/junit.xml"
    fi
    
    if [ -f "test_results/coverage.xml" ]; then
        echo "Coverage XML: test_results/coverage.xml"
    fi
    
    if [ -f "test_results/report.html" ]; then
        echo "HTML Report: test_results/report.html"
    fi
    
    if [ -d "test_results/htmlcov" ]; then
        echo "Coverage HTML: test_results/htmlcov/index.html"
    fi
    
    echo ""
    print_status "To view coverage report:"
    echo "  open test_results/htmlcov/index.html"
    
    print_status "To view HTML report:"
    echo "  open test_results/report.html"
}

# Function to run specific test module
run_module_tests() {
    local module_name=$1
    if [ -z "$module_name" ]; then
        print_error "Module name is required"
        echo "Usage: $0 module <module_name>"
        exit 1
    fi
    
    print_status "Running tests for module: $module_name"
    docker-compose -f docker-compose.test.yml run --rm all_tests -k "$module_name"
    print_success "Module tests completed for: $module_name"
}

# Function to run tests with specific markers
run_marker_tests() {
    local marker=$1
    if [ -z "$marker" ]; then
        print_error "Marker is required"
        echo "Usage: $0 marker <marker_name>"
        exit 1
    fi
    
    print_status "Running tests with marker: $marker"
    docker-compose -f docker-compose.test.yml run --rm all_tests -m "$marker"
    print_success "Marker tests completed for: $marker"
}

# Function to show help
show_help() {
    echo "Odoo Enterprise Features - Test Script"
    echo "======================================"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  unit              Run unit tests only"
    echo "  integration       Run integration tests only"
    echo "  e2e               Run end-to-end tests only"
    echo "  performance       Run performance tests only"
    echo "  security          Run security tests only"
    echo "  all               Run all tests (default)"
    echo "  module <name>     Run tests for specific module"
    echo "  marker <name>     Run tests with specific marker"
    echo "  coverage          Generate coverage report"
    echo "  clean             Clean up test containers"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit                    # Run unit tests"
    echo "  $0 module vehicle_management  # Run vehicle management tests"
    echo "  $0 marker enterprise       # Run enterprise feature tests"
    echo "  $0 all                     # Run all tests"
    echo ""
}

# Main script logic
main() {
    local command=${1:-all}
    
    case $command in
        "unit")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_unit_tests
            generate_coverage_report
            show_results
            ;;
        "integration")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_integration_tests
            generate_coverage_report
            show_results
            ;;
        "e2e")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_e2e_tests
            generate_coverage_report
            show_results
            ;;
        "performance")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_performance_tests
            generate_coverage_report
            show_results
            ;;
        "security")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_security_tests
            generate_coverage_report
            show_results
            ;;
        "all")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_all_tests
            generate_coverage_report
            show_results
            ;;
        "module")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_module_tests "$2"
            generate_coverage_report
            show_results
            ;;
        "marker")
            check_docker
            check_docker_compose
            build_images
            start_test_db
            wait_for_db
            run_marker_tests "$2"
            generate_coverage_report
            show_results
            ;;
        "coverage")
            generate_coverage_report
            show_results
            ;;
        "clean")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"




