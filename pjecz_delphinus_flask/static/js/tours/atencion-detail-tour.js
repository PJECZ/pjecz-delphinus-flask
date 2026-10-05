import { registerTour } from './tour-manager.js';

function addStep(steps, selector, title, description) {
    const element = document.querySelector(selector);
    if (!element) {
        return;
    }
    steps.push({
        element,
        disableActiveInteraction: true,
        popover: {
            title,
            description,
            side: window.innerWidth < 576 ? 'top' : 'bottom',
            align: window.innerWidth < 576 ? 'center' : 'start',
        },
    });
}

function createDetailSteps() {
    const steps = [];
    addStep(
        steps,
        '[data-tour-detail="summary"]',
        'Detalle de la atención',
        'En esta sección puedes consultar los datos registrados de la atención, como las personas, el trámite, el expediente y las observaciones.',
    );
    addStep(
        steps,
        '[data-subsecuente-link]',
        'Crear subsecuente',
        'Permite iniciar una atención subsecuente. El sistema reutiliza el actor, la contraparte y el tipo de trámite de la atención actual.',
    );
    addStep(
        steps,
        '[data-tour-edit]',
        'Editar atención',
        'Utiliza Editar para actualizar información, incluidas las observaciones, la fecha de siguiente cita o el estado.',
    );
    addStep(
        steps,
        '[data-tour-print]',
        'Imprimir resumen',
        'Utiliza esta opción para generar el resumen imprimible de la atención.',
    );
    return steps;
}

registerTour('atencion-detail', createDetailSteps);
