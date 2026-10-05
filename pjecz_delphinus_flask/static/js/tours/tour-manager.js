import { driver } from 'https://cdn.jsdelivr.net/npm/driver.js@1.8.0/+esm';

const sharedConfig = {
    animate: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    duration: 350,
    overlayColor: 'rgba(15, 23, 42, 0.68)',
    overlayOpacity: 0.55,
    smoothScroll: true,
    allowClose: true,
    allowScroll: true,
    allowKeyboardControl: true,
    overlayClickBehavior: 'none',
    showProgress: true,
    progressText: 'Paso {{current}} de {{total}}',
    nextBtnText: 'Siguiente',
    prevBtnText: 'Anterior',
    doneBtnText: 'Finalizar',
    closeBtnLabel: 'Cerrar tutorial',
    popoverClass: 'defensoria-driver-popover',
    popoverOffset: 12,
    onPopoverRender: popover => {
        popover.closeButton.setAttribute('aria-label', 'Cerrar tutorial');
    },
    onHighlightStarted: element => {
        if (!element) {
            return;
        }
        const bounds = element.getBoundingClientRect();
        const outsideViewport = bounds.top < 0 || bounds.bottom > document.documentElement.clientHeight;
        if (outsideViewport) {
            element.scrollIntoView({
                behavior: 'auto',
                block: 'center',
                inline: 'nearest',
            });
        }
    },
    stagePadding: 8,
    stageRadius: 6,
};

let activeTour = null;
const tourFactories = new Map();

function preventPageActions(event) {
    if (!activeTour || event.target.closest('.driver-popover')) {
        return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
}

export function createTour(steps, options = {}) {
    return driver({
        ...sharedConfig,
        ...options,
        steps,
    });
}

export function startTour(steps, options = {}) {
    if (!steps.length) {
        return null;
    }
    activeTour?.destroy();
    let finalized = false;
    let tour;
    const finalize = () => {
        if (finalized) {
            return;
        }
        finalized = true;
        document.removeEventListener('click', preventPageActions, true);
        options.onDestroyed?.();
        if (activeTour === tour) {
            activeTour = null;
        }
    };
    tour = createTour(steps, {
        ...options,
        onDestroyStarted: (_element, _step, hookOptions) => {
            finalize();
            hookOptions.driver.destroy();
        },
        onDestroyed: finalize,
    });
    activeTour = tour;
    document.addEventListener('click', preventPageActions, true);
    activeTour.drive();
    return activeTour;
}

export function closeActiveTour() {
    activeTour?.destroy();
    activeTour = null;
}

export function registerTour(name, createSteps) {
    tourFactories.set(name, createSteps);
}

document.addEventListener('click', event => {
    const button = event.target.closest('[data-tour-help]');
    if (!button) {
        return;
    }
    const createSteps = tourFactories.get(button.dataset.tourHelp);
    if (!createSteps) {
        return;
    }
    event.preventDefault();
    const tour = createSteps();
    startTour(tour.steps || tour, {
        onDestroyed: () => {
            tour.cleanup?.();
        },
    });
});
