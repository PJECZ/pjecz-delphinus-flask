import { registerTour } from './tour-manager.js';

function addStep(steps, root, selector, title, description, options = {}) {
    const target = root.querySelector(selector);
    if (!target) {
        return;
    }
    steps.push({
        element: target,
        disableActiveInteraction: true,
        popover: {
            title,
            description,
            side: options.side || (window.innerWidth < 576 ? 'top' : 'bottom'),
            align: window.innerWidth < 576 ? 'center' : 'start',
        },
    });
}

function addPersonSteps(steps, root, role, label) {
    const panel = root.querySelector(`[data-person-role="${role}"]`);
    if (!panel) {
        return;
    }
    addStep(
        steps,
        panel,
        '.atencion-person-panel__heading',
        label,
        `Busca y selecciona a ${role === 'actor' ? 'la persona principal' : 'la persona relacionada'} con la atención.`,
    );
    addStep(
        steps,
        panel,
        '[data-search-fields]',
        `Buscar ${label.toLowerCase()}`,
        'Captura el nombre y los apellidos que conozcas para localizar a la persona.',
    );
    addStep(
        steps,
        panel,
        '[data-action="search"]',
        `Buscar ${label.toLowerCase()}`,
        `Al usar “Buscar ${role}”, el sistema consulta las personas registradas.`,
    );
    addStep(
        steps,
        panel,
        '[data-search-results]',
        `Resultados de ${label.toLowerCase()}`,
        'Aquí aparecerán las coincidencias. Selecciona el registro que corresponda.',
    );

    addStep(
        steps,
        panel,
        '[data-search-results]',
        'Seleccionar persona',
        'Cuando se muestren los resultados, elige el registro correcto para consultar sus atenciones.',
    );

    addStep(
        steps,
        panel,
        '[data-action="register"]',
        'Registrar nueva persona',
        `Si no encuentras a ${role === 'actor' ? 'la persona' : 'la contraparte'}, puedes iniciar el registro desde esta opción.`,
    );
    if (panel.querySelector('[data-person-registration]')) {
        steps.push({
            element: panel.querySelector('[data-person-registration]'),
            disableActiveInteraction: true,
            popover: {
                title: 'Completar registro',
                description: 'Este formulario permite completar los datos de la persona. Los campos de nombre y apellidos pueden editarse antes de guardar.',
                side: 'top',
                align: 'start',
            },
        });
        steps.push({
            element: panel.querySelector('[data-person-registration] [type="submit"]'),
            disableActiveInteraction: true,
            popover: {
                title: 'Guardar y seleccionar',
                description: 'Al guardar el formulario, la nueva persona quedará seleccionada para continuar. El tutorial no realiza el registro.',
                side: 'top',
                align: 'start',
            },
        });
    }
}

function createIndexSteps() {
    const root = document.querySelector('#atencionFormContainer .atencion-module');
    if (!root) {
        return { steps: [] };
    }

    const registrations = [...root.querySelectorAll('[data-person-registration]')];
    const previousRegistrationVisibility = registrations.map(form => form.classList.contains('d-none'));
    registrations.forEach(form => form.classList.remove('d-none'));

    const steps = [];
    addStep(
        steps,
        root,
        '.atencion-module__header',
        'Actor y contraparte',
        'Aquí puedes buscar a las personas relacionadas con una atención. Primero identifica al actor y, cuando corresponda, a su contraparte.',
    );
    addPersonSteps(steps, root, 'actor', 'Actor');
    addStep(
        steps,
        root,
        '.atencion-related__heading',
        'Atenciones relacionadas',
        'Después de seleccionar una persona, aquí consultarás sus atenciones. Cuando ambas personas están seleccionadas, se muestran las atenciones en las que participan ambas.',
    );
    addPersonSteps(steps, root, 'contraparte', 'Contraparte');
    addStep(
        steps,
        root,
        '.atencion-related__list',
        'Atenciones de ambas personas',
        'Al seleccionar un actor y una contraparte, aquí aparecen las atenciones registradas entre ambas personas. Desde los resultados puedes abrir el detalle.',
    );
    if (root.querySelector('[data-action="new-attention"]')) {
        addStep(
            steps,
            root,
            '.atencion-related__heading',
            'Crear nueva atención',
            'Si ambas personas están seleccionadas y no hay atenciones relacionadas, la opción para crear una nueva atención aparece en esta sección.',
        );
    }

    return {
        steps,
        cleanup: () => {
            registrations.forEach((form, index) => {
                form.classList.toggle('d-none', previousRegistrationVisibility[index]);
            });
        },
    };
}

registerTour('index', createIndexSteps);
