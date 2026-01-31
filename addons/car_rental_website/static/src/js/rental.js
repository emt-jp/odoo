/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date constraints
    initDateConstraints();

    // Initialize availability checker
    initAvailabilityChecker();

    // Initialize price calculator
    initPriceCalculator();
});

function initDateConstraints() {
    const pickupDate = document.querySelector('input[name="pickup_date"]');
    const dropoffDate = document.querySelector('input[name="dropoff_date"]');

    if (!pickupDate || !dropoffDate) return;

    // Set minimum date to today
    const today = new Date().toISOString().split('T')[0];
    pickupDate.setAttribute('min', today);

    // Update dropoff min date when pickup changes
    pickupDate.addEventListener('change', function() {
        if (this.value) {
            dropoffDate.setAttribute('min', this.value);
            if (dropoffDate.value && dropoffDate.value < this.value) {
                dropoffDate.value = this.value;
            }
        }
    });

    // Validate dropoff is after pickup
    dropoffDate.addEventListener('change', function() {
        if (pickupDate.value && this.value < pickupDate.value) {
            alert('Return date must be after pickup date');
            this.value = pickupDate.value;
        }
    });
}

function initAvailabilityChecker() {
    const vehicleId = document.querySelector('input[name="vehicle_id"]');
    const pickupDate = document.querySelector('input[name="pickup_date"]');
    const dropoffDate = document.querySelector('input[name="dropoff_date"]');

    if (!vehicleId || !pickupDate || !dropoffDate) return;

    async function checkAvailability() {
        if (!pickupDate.value || !dropoffDate.value) return;

        try {
            const response = await fetch('/cars/check-availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        vehicle_id: vehicleId.value,
                        pickup_date: pickupDate.value,
                        dropoff_date: dropoffDate.value,
                    },
                }),
            });

            const data = await response.json();
            if (data.result && !data.result.available) {
                alert('This vehicle is not available for the selected dates. Please choose different dates.');
            }
        } catch (error) {
            console.error('Error checking availability:', error);
        }
    }

    pickupDate.addEventListener('change', checkAvailability);
    dropoffDate.addEventListener('change', checkAvailability);
}

function initPriceCalculator() {
    // Add live price calculation if needed
    const insuranceRadios = document.querySelectorAll('input[name="insurance"]');
    const extraCheckboxes = document.querySelectorAll('.extra-checkbox');

    insuranceRadios.forEach(radio => {
        radio.addEventListener('change', updatePriceSummary);
    });

    extraCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updatePriceSummary);
    });
}

function updatePriceSummary() {
    // Price summary will be calculated server-side after form submission
    // This function can be extended for live price updates via AJAX
}

// Smooth scroll to booking form
function scrollToBookingForm() {
    const form = document.querySelector('.booking-form');
    if (form) {
        form.scrollIntoView({ behavior: 'smooth' });
    }
}

// Copy booking reference to clipboard
function copyBookingRef(ref) {
    navigator.clipboard.writeText(ref).then(() => {
        alert('Booking reference copied to clipboard!');
    });
}
