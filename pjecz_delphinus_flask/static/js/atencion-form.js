(() => {
    const module = document.querySelector('#atencionFormContainer .atencion-module');
    if (!module) {
        return;
    }

    const selectedPeople = { actor: null, contraparte: null };
    const catalogRequests = new Map();
    const registrationRequests = new WeakMap();
    let attentionRequest = 0;
    let attentionFormRequest = 0;

    function getPanel(element) {
        return element.closest('[data-person-role]');
    }

    function closeRegistration(panel) {
        registrationRequests.set(panel, (registrationRequests.get(panel) || 0) + 1);
        panel.querySelector('[data-person-registration]')?.classList.add('d-none');
    }

    function showPanelMessage(panel, message, kind = 'muted') {
        const results = panel.querySelector('[data-search-results]');
        const status = results.querySelector('p');
        const list = results.querySelector('ul');
        status.className = `small mb-2 text-${kind}`;
        status.textContent = message;
        list.replaceChildren();
        list.hidden = true;
        results.querySelector('[data-action="load-more"]')?.remove();
        results.removeAttribute('aria-busy');
    }

    function getSearchParameters(panel) {
        return [...panel.querySelectorAll('[data-search-field]')].reduce((params, input) => {
            const value = input.value.trim();
            if (value) {
                params.set(input.dataset.searchField, value);
            }
            return params;
        }, new URLSearchParams());
    }

    function personName(person) {
        return [person.nombres, person.apellido_primero, person.apellido_segundo]
            .filter(Boolean)
            .join(' ');
    }

    function addSearchResult(panel, person) {
        const list = panel.querySelector('[data-search-results] ul');
        const item = document.createElement('li');
        item.className = 'list-group-item p-0';
        const button = document.createElement('button');
        button.className = 'list-group-item list-group-item-action border-0 w-100 text-start';
        button.type = 'button';
        button.dataset.action = 'select-person';
        button.dataset.personId = person.id;
        button.dataset.personName = personName(person);
        const name = document.createElement('span');
        name.className = 'd-block fw-semibold';
        name.textContent = button.dataset.personName;
        button.append(name);
        if (person.curp) {
            const curp = document.createElement('small');
            curp.className = 'd-block text-body-secondary';
            curp.textContent = person.curp;
            button.append(curp);
        }
        item.append(button);
        list.append(item);
    }

    async function searchPeople(panel, page = 1) {
        closeRegistration(panel);
        const searchButton = panel.querySelector('[data-action="search"]');
        if (searchButton.disabled) {
            return;
        }
        const parameters = getSearchParameters(panel);
        if (!parameters.size) {
            showPanelMessage(panel, 'Ingresa al menos un criterio para buscar.', 'warning');
            panel.querySelector('[data-search-field]').focus();
            return;
        }

        const results = panel.querySelector('[data-search-results]');
        const list = results.querySelector('ul');
        const status = results.querySelector('p');
        searchButton.disabled = true;
        results.setAttribute('aria-busy', 'true');
        results.querySelector('[data-action="load-more"]')?.remove();
        if (page === 1) {
            list.replaceChildren();
            list.hidden = true;
        }
        status.className = 'small mb-2 text-body-secondary';
        status.textContent = page === 1 ? 'Buscando personas...' : 'Cargando más resultados...';

        const requestUrl = new URL(module.dataset.personSearchUrl, window.location.href);
        parameters.set('page', page);
        requestUrl.search = parameters.toString();
        try {
            const response = await fetch(requestUrl, { headers: { Accept: 'application/json' } });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'No fue posible buscar personas.');
            }
            data.results.forEach(person => addSearchResult(panel, person));
            list.hidden = data.results.length === 0 && page === 1;
            status.textContent = list.children.length ? 'Selecciona una persona de los resultados.' : 'No se encontraron personas.';
            panel.dataset.page = String(page);
            if (data.pagination.more) {
                const loadMore = document.createElement('button');
                loadMore.className = 'btn btn-sm btn-outline-secondary mt-2';
                loadMore.type = 'button';
                loadMore.dataset.action = 'load-more';
                loadMore.textContent = 'Cargar más resultados';
                results.append(loadMore);
            }
        } catch (error) {
            status.className = 'small mb-2 text-danger';
            status.textContent = error.message || 'Ocurrió un error al buscar personas.';
        } finally {
            searchButton.disabled = false;
            results.removeAttribute('aria-busy');
        }
    }

    function updateSelectedPerson(role) {
        console.log('Updating selected person for role:', role);

        const panel = module.querySelector(`[data-person-role="${role}"]`);
        const person = selectedPeople[role];
        const empty = panel.querySelector('[data-selected-empty]');
        const selected = panel.querySelector('[data-selected-person]');
        empty.hidden = Boolean(person);
        selected.hidden = !person;
        if (person) {
            selected.setAttribute('role', 'status');
            selected.setAttribute('aria-live', 'polite');
            selected.querySelector('[data-person-name]').textContent = person.nombre_completo;
            selected.tabIndex = -1;
            selected.focus();
        }
    }

    function scrollToElement(element) {
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        element.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    }

    function setAttentionState(state) {
        module.querySelectorAll('[data-attention-state]').forEach(element => {
            element.hidden = element.dataset.attentionState !== state;
        });
        const related = module.querySelector('.atencion-related');
        related.toggleAttribute('aria-busy', state === 'loading');
        const results = module.querySelector('[data-attention-results]');
        if (state !== 'results') {
            results.replaceChildren();
            results.hidden = true;
        }
    }

    function clearAttentionSaveStatus() {
        const status = module.querySelector('[data-attention-save-status]');
        status.hidden = true;
        status.textContent = '';
    }

    function appendAttention(atencion) {
        console.log('Appending attention:', atencion);
        const item = document.createElement('li');
        item.className = 'list-group-item';
        const link = document.createElement('a');
        link.className = 'fw-semibold';
        link.href = atencion.url;
        link.textContent = atencion.folio ? `Folio ${atencion.folio}` : `Atención ${atencion.id}`;
        item.append(link);

        const details = document.createElement('div');
        details.className = 'd-flex flex-wrap gap-2 mt-1 small text-body-secondary';
        [atencion.fecha, atencion.tipo, atencion.tipo_atencion, atencion.expediente, atencion.participacion]
            .filter(Boolean)
            .forEach(value => {
                const detail = document.createElement('span');
                detail.textContent = value;
                details.append(detail);
            });
        item.append(details);
        module.querySelector('[data-attention-results]').append(item);
    }

    async function refreshAttentions() {
        const requestId = ++attentionRequest;
        const actor = selectedPeople.actor;
        console.log('Selected actor:', actor);
        const contraparte = selectedPeople.contraparte;
        console.log('Selected contraparte:', contraparte);
        const heading = module.querySelector('#atenciones-relacionadas-title');
        const results = module.querySelector('[data-attention-results]');
        const params = new URLSearchParams();
        if (actor) params.set('udp_persona_id', actor.id);
        if (contraparte) params.set('contraparte_id', contraparte.id);

        heading.textContent = actor && contraparte
            ? 'Atenciones entre ' + actor.nombre_completo + ' - ' + contraparte.nombre_completo
            : actor
                ? 'Atenciones relacionadas de ' + actor.nombre_completo
                : contraparte
                    ? 'Atenciones relacionadas de ' + contraparte.nombre_completo
                    : 'Atenciones relacionadas';

        if (!actor && !contraparte) {
            setAttentionState('initial');
            return;
        }

        setAttentionState('loading');
        const requestUrl = new URL(module.dataset.attentionsUrl, window.location.href);
        requestUrl.search = params.toString();
        try {
            const response = await fetch(requestUrl, { headers: { Accept: 'application/json' } });
            const data = await response.json();
            if (requestId !== attentionRequest) {
                return;
            }
            if (!response.ok) {
                throw new Error(data.error || 'No fue posible consultar las atenciones.');
            }
            if (!data.results.length) {
                setAttentionState(actor && contraparte ? 'empty-pair' : 'empty-person');
                return;
            }
            data.results.forEach(appendAttention);
            results.hidden = false;
            setAttentionState('results');
            if (data.pagination.more) {
                const notice = document.createElement('li');
                notice.className = 'list-group-item small text-body-secondary';
                notice.textContent = 'Se muestran las 50 atenciones más recientes.';
                results.append(notice);
            }
        } catch (error) {
            if (requestId !== attentionRequest) {
                return;
            }
            setAttentionState('error');
            const state = module.querySelector('[data-attention-state="error"]');
            if (!state) {
                const errorState = document.createElement('div');
                errorState.className = 'atencion-related__state text-danger';
                errorState.dataset.attentionState = 'error';
                errorState.setAttribute('role', 'alert');
                module.querySelector('.atencion-related').append(errorState);
                errorState.textContent = error.message || 'Ocurrió un error al consultar atenciones.';
            } else {
                state.textContent = error.message || 'Ocurrió un error al consultar atenciones.';
            }
        }
    }

    async function loadCatalog(select, url, valueField = 'id') {
        if (select.dataset.loaded === 'true') {
            return;
        }
        if (!catalogRequests.has(url)) {
            catalogRequests.set(url, fetch(url, { headers: { Accept: 'application/json' } })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('No fue posible cargar las opciones del formulario.');
                    }
                    return response.json();
                }));
        }
            let data;
            try {
                data = await catalogRequests.get(url);
            } catch (error) {
                catalogRequests.delete(url);
                throw error;
            }
        data.results.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueField];
            option.textContent = item.text;
            select.append(option);
        });
        select.dataset.loaded = 'true';
    }

    async function initializeInlineAttentionForm(config) {
        const form = config.querySelector('#atencion_form');
        const tipoTramite = form.elements.udp_tipo_tramite;
        const distrito = form.elements.distrito;
        const autoridad = form.elements.autoridad;
        const defensor = form.elements.defensor;
        const visita = form.elements.visita;

        await Promise.all([
            loadCatalog(tipoTramite, config.dataset.tipoTramiteUrl),
            loadCatalog(distrito, config.dataset.distritosUrl),
            loadCatalog(visita, config.dataset.visitasUrl, 'text'),
            loadCatalog(defensor, config.dataset.defensoresUrl),
        ]);

        distrito.value = config.dataset.distritoId || distrito.options[0]?.value || '';
        let authorityRequest = 0;
        async function loadAuthorities() {
            const requestId = ++authorityRequest;
            const districtId = distrito.value;
            autoridad.replaceChildren(new Option('Seleccionar autoridad', ''));
            if (!districtId) {
                return;
            }
            const url = new URL(config.dataset.autoridadesUrl, window.location.href);
            url.searchParams.set('distrito_id', districtId);
            const response = await fetch(url, { headers: { Accept: 'application/json' } });
            const data = await response.json();
            if (requestId !== authorityRequest || distrito.value !== districtId) {
                return;
            }
            if (!response.ok) {
                throw new Error(data.error || 'No fue posible cargar las autoridades.');
            }
            data.results.forEach(item => autoridad.add(new Option(item.text, item.id)));
            autoridad.value = districtId === config.dataset.distritoId
                ? config.dataset.autoridadId
                : '';
            if (!autoridad.value && autoridad.options.length > 1) {
                autoridad.selectedIndex = 1;
            }
        }
        distrito.addEventListener('change', loadAuthorities);
        await loadAuthorities();
        if (config.dataset.defensorId) {
            defensor.value = config.dataset.defensorId;
        }
        const contraparteSelect = form.elements.udp_contraparte;
        if (!contraparteSelect.value) {
            throw new Error('La contraparte seleccionada no está asociada al formulario.');
        }
        form.querySelector('[name="udp_persona_id"]').value = selectedPeople.actor.id;
    }

    function setNewAttentionError(content, message) {
        const error = document.createElement('div');
        error.className = 'alert alert-danger mb-0';
        error.setAttribute('role', 'alert');
        error.textContent = message;
        content.replaceChildren(error);
    }

    async function openNewAttention(button) {
        const actor = selectedPeople.actor;
        const contraparte = selectedPeople.contraparte;
        if (!actor || !contraparte || button.disabled) {
            return;
        }
        const requestId = ++attentionFormRequest;

        const mount = module.querySelector('[data-new-attention-form]');
        const content = mount.querySelector('[data-new-attention-content]');
        mount.hidden = false;
        button.disabled = true;
        if (content.querySelector('#atencion_form')) {
            button.disabled = false;
            scrollToElement(mount);
            return;
        }

        const loading = document.createElement('p');
        loading.className = 'text-body-secondary';
        loading.setAttribute('role', 'status');
        loading.textContent = 'Cargando formulario...';
        content.replaceChildren(loading);
        const url = new URL(module.dataset.newAttentionUrl, window.location.href);
        url.searchParams.set('udp_persona_id', actor.id);
        url.searchParams.set('contraparte_id', contraparte.id);
        try {
            const response = await fetch(url, { headers: { Accept: 'text/html' } });
            const html = await response.text();
            if (requestId !== attentionFormRequest
                || selectedPeople.actor?.id !== actor.id
                || selectedPeople.contraparte?.id !== contraparte.id) {
                return;
            }
            if (!response.ok) {
                throw new Error('No fue posible abrir el formulario de nueva atención.');
            }
            content.innerHTML = html;
            const config = content.querySelector('[data-inline-atencion-config]');
            if (!config) {
                throw new Error('La respuesta no contiene el formulario esperado.');
            }
            await initializeInlineAttentionForm(config);
            if (requestId === attentionFormRequest) {
                module.querySelector('#udp_tipo_tramite')?.focus();
            }
        } catch (error) {
            setNewAttentionError(content, error.message || 'Ocurrió un error al abrir el formulario.');
        } finally {
            button.disabled = false;
        }
        scrollToElement(mount);
    }

    function closeNewAttention(returnFocus = false) {
        attentionFormRequest += 1;
        const mount = module.querySelector('[data-new-attention-form]');
        mount.hidden = true;
        if (returnFocus) {
            module.querySelector('[data-action="new-attention"]')?.focus();
        }
    }

    async function openRegistration(panel) {
        const form = panel.querySelector('[data-person-registration]');
        if (!form) {
            return;
        }
        const requestId = (registrationRequests.get(panel) || 0) + 1;
        registrationRequests.set(panel, requestId);
        ['nombres', 'apellido_primero', 'apellido_segundo'].forEach(name => {
            const source = panel.querySelector(`[data-search-field="${name}"]`);
            const target = form.elements.namedItem(name);
            target.value = source.value.trim();
        });
        const feedback = form.querySelector('[data-registration-feedback]');
        const registerButton = panel.querySelector('[data-action="register"]');
        registerButton.disabled = true;
        feedback.className = 'small mt-2 mb-0 text-body-secondary';
        feedback.textContent = 'Cargando opciones...';
        try {
            await Promise.all([
                loadCatalog(form.elements.udp_sexo, module.dataset.sexUrl),
                loadCatalog(form.elements.udp_tipo_condicion, module.dataset.conditionUrl),
            ]);
            if (registrationRequests.get(panel) !== requestId) {
                return;
            }
            form.classList.remove('d-none');
            feedback.textContent = '';
            form.querySelector('[name="nombres"]').focus();
        } catch (error) {
            if (registrationRequests.get(panel) !== requestId) {
                return;
            }
            feedback.className = 'small mt-2 mb-0 text-danger';
            feedback.textContent = error.message;
        } finally {
            registerButton.disabled = false;
        }
    }

    async function submitRegistration(form) {
        const panel = getPanel(form);
        const feedback = form.querySelector('[data-registration-feedback]');
        if (!form.reportValidity()) {
            return;
        }
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        feedback.className = 'small mt-2 mb-0 text-body-secondary';
        feedback.textContent = 'Guardando persona...';
        const formData = new FormData(form);
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (csrfToken) {
            formData.set('csrf_token', csrfToken);
        }
        try {
            const response = await fetch(module.dataset.personCreateUrl, {
                method: 'POST',
                headers: { 'X-CSRF-TOKEN': csrfToken || '', Accept: 'application/json' },
                body: formData,
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'No fue posible registrar a la persona.');
            }
            const role = panel.dataset.personRole;
            selectedPeople[role] = { id: data.persona.id, nombre_completo: data.persona.nombre_completo };
            clearAttentionSaveStatus();
            closeNewAttention();
            module.querySelector('[data-new-attention-content]').replaceChildren();
            updateSelectedPerson(role);
            form.reset();
            form.classList.add('d-none');
            showPanelMessage(panel, data.avisos.length ? data.avisos.join(' ') : 'Persona registrada y seleccionada.', data.avisos.length ? 'warning' : 'success');
            await refreshAttentions();
        } catch (error) {
            feedback.className = 'small mt-2 mb-0 text-danger';
            feedback.textContent = error.message || 'Ocurrió un error al registrar a la persona.';
        } finally {
            submit.disabled = false;
        }
    }

    async function submitInlineAttention(form) {
        if (!form.reportValidity()) {
            return;
        }
        const config = form.closest('[data-inline-atencion-config]');
        const feedback = config.querySelector('[data-inline-save-feedback]');
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        form.setAttribute('aria-busy', 'true');
        feedback.className = 'alert alert-info';
        feedback.textContent = 'Guardando atención...';

        try {
            const response = await fetch(form.action, {
                method: form.method.toUpperCase(),
                headers: {
                    Accept: 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: new FormData(form),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                const fieldError = Object.values(data.errors || {}).flat().find(Boolean);
                throw new Error(data.error || fieldError || 'No fue posible guardar la atención.');
            }

            const saveStatus = module.querySelector('[data-attention-save-status]');
            saveStatus.textContent = data.message || 'La atención se guardó correctamente.';
            saveStatus.hidden = false;
            closeNewAttention();
            await refreshAttentions();
            const heading = module.querySelector('#atenciones-relacionadas-title');
            heading.tabIndex = -1;
            heading.focus();
        } catch (error) {
            feedback.className = 'alert alert-danger';
            feedback.setAttribute('role', 'alert');
            feedback.textContent = error.message || 'Ocurrió un error al guardar la atención.';
        } finally {
            submit.disabled = false;
            form.removeAttribute('aria-busy');
        }
    }

    module.addEventListener('click', event => {
        const button = event.target.closest('button[data-action]');
        if (!button || !module.contains(button)) {
            return;
        }
        const panel = getPanel(button);
        switch (button.dataset.action) {
            case 'search':
                searchPeople(panel);
                break;
            case 'load-more':
                searchPeople(panel, Number(panel.dataset.page || 1) + 1);
                break;
            case 'select-person': {
                const role = panel.dataset.personRole;
                selectedPeople[role] = { id: button.dataset.personId, nombre_completo: button.dataset.personName };
                clearAttentionSaveStatus();
                closeNewAttention();
                module.querySelector('[data-new-attention-content]').replaceChildren();
                updateSelectedPerson(role);
                closeRegistration(panel);
                showPanelMessage(panel, 'Persona seleccionada.', 'success');
                refreshAttentions();
                break;
            }
            case 'clear': {
                const role = panel.dataset.personRole;
                selectedPeople[role] = null;
                clearAttentionSaveStatus();
                closeNewAttention();
                module.querySelector('[data-new-attention-content]').replaceChildren();
                updateSelectedPerson(role);
                panel.querySelector('[data-action="search"]').focus();
                refreshAttentions();
                break;
            }
            case 'register':
                openRegistration(panel);
                break;
            case 'cancel-register':
                closeRegistration(panel);
                panel.querySelector('[data-action="register"]').focus();
                break;
            case 'new-attention':
                openNewAttention(button);
                break;
            case 'close-new-attention':
                closeNewAttention(true);
                break;
            default:
                break;
        }
    });

    module.addEventListener('submit', event => {
        if (event.target.matches('[data-inline-atencion-config] #atencion_form')) {
            event.preventDefault();
            submitInlineAttention(event.target);
            return;
        }
        if (event.target.matches('[data-person-registration]')) {
            event.preventDefault();
            submitRegistration(event.target);
        }
    });

    module.addEventListener('keydown', event => {
        if (event.key === 'Enter' && event.target.matches('[data-search-field]')) {
            event.preventDefault();
            searchPeople(getPanel(event.target));
        }
    });
})();
