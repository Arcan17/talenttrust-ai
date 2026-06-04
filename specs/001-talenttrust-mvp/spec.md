# Feature Specification: AI Candidate Dossier (TalentTrust AI — MVP Phase 1)

**Feature Branch**: `001-talenttrust-mvp`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "TalentTrust AI — copiloto B2B para recruiters que convierte un CV (PDF/DOCX) + una vacante estructurada en un dossier verificable y explicable del candidato (score 0–100 explicable, resumen, skills con evidencia, brechas, inconsistencias neutrales, preguntas de entrevista, recomendación no vinculante). El recruiter registra la decisión humana final y puede exportar el dossier a PDF."

## Clarifications

### Session 2026-06-04

- Q: ¿Qué factores compondrán el desglose del score 0–100? → A: 6 factores con pesos fijos que suman
  100 — skills/stack obligatorias (35), experiencia relevante (20), seniority (15),
  modalidad/ubicación (10), evidencia/soporte (10), penalización por inconsistencias (10).
- Q: ¿Qué señales de inconsistencia detecta la Fase 1? → A: Set completo (unión): fechas laborales
  solapadas/ilógicas, gaps temporales grandes, seniority declarado vs años de experiencia, skill
  declarada sin evidencia en el cuerpo del CV, idioma declarado vs idioma del CV, educación
  incompleta/ambigua, y certificaciones mencionadas sin detalle verificable.
- Q: ¿Política de retención/borrado de datos del candidato? → A: Borrado on-demand (hard delete) a
  solicitud + TTL por defecto configurable por variable de entorno (ej. 180 días); sin purga
  automática obligatoria en Fase 1.
- Q: ¿Idiomas soportados del CV? → A: Español e inglés (parseo y dossier optimizados para español con
  tolerancia a contenido en inglés); UI en español.
- Q: ¿Límites de tipo y tamaño del archivo de CV? → A: Solo PDF y DOCX con texto extraíble, máximo
  5 MB; PDFs escaneados como imagen (sin texto) se rechazan con error claro (OCR fuera de alcance).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recruiter crea una vacante estructurada (Priority: P1)

Un recruiter, tras iniciar sesión en su organización, crea una vacante describiendo el cargo y sus
requisitos estructurados: título, descripción, skills obligatorias, skills deseables, modalidad
(remoto/híbrido/presencial), país/zona, rango salarial y seniority esperado. La vacante queda
guardada y disponible para evaluar candidatos contra ella.

**Why this priority**: Sin una vacante estructurada no existe un referente contra el cual calcular
compatibilidad ni detectar brechas. Es el cimiento de todo el dossier y, por sí sola, ya ordena el
criterio de búsqueda del recruiter.

**Independent Test**: Se puede probar creando una vacante con todos sus campos y verificando que se
persiste, se lista y se recupera correctamente dentro de la organización del recruiter (y nunca es
visible para otra organización).

**Acceptance Scenarios**:

1. **Given** un recruiter autenticado, **When** crea una vacante con título, descripción, skills
   obligatorias y deseables, modalidad, país, rango salarial y seniority, **Then** la vacante se
   guarda y aparece en el listado de vacantes de su organización.
2. **Given** una vacante con un campo obligatorio faltante (p. ej. título o skills obligatorias),
   **When** el recruiter intenta crearla, **Then** el sistema rechaza la creación con un mensaje de
   validación claro.
3. **Given** una vacante creada en la organización A, **When** un recruiter de la organización B
   consulta sus vacantes, **Then** la vacante de A no aparece ni es accesible.

---

### User Story 2 - Recruiter sube un CV con consentimiento y obtiene un dossier explicable (Priority: P1)

El recruiter selecciona una vacante, sube el CV de un candidato en PDF o DOCX y declara que cuenta
con el consentimiento del candidato para el análisis. El sistema extrae los datos del CV, calcula un
score de compatibilidad 0–100 explicable (con desglose por factor y la fuente de cada conclusión) y
genera un dossier: resumen profesional, skills detectadas con su evidencia, brechas frente a la
vacante, inconsistencias en lenguaje neutral, preguntas de entrevista sugeridas y una recomendación
NO vinculante. El consentimiento queda registrado y versionado.

**Why this priority**: Es el núcleo de valor del producto. Convierte un CV crudo en una evaluación
trazable contra la vacante. Junto con la US1 forma el MVP mínimo demostrable.

**Independent Test**: Subiendo un CV de prueba contra una vacante existente y verificando que se
genera un dossier con score numérico, desglose que reconcilia al total, skills con evidencia y un
registro de consentimiento versionado — todo de forma reproducible para el mismo CV y vacante.

**Acceptance Scenarios**:

1. **Given** una vacante y un CV PDF válido con consentimiento declarado, **When** el recruiter sube
   el CV, **Then** el sistema extrae los datos, genera el dossier y muestra un score 0–100 con su
   desglose por factor.
2. **Given** un dossier generado, **When** el recruiter revisa cualquier conclusión (skill, brecha,
   inconsistencia), **Then** cada conclusión muestra la fuente/evidencia que la respalda.
3. **Given** el mismo CV y la misma vacante, **When** se genera el dossier dos veces, **Then** el
   score numérico y su desglose son idénticos.
4. **Given** un CV que se sube sin declarar consentimiento, **When** el recruiter intenta generar el
   dossier, **Then** el sistema no procesa el análisis y solicita el consentimiento.
5. **Given** un CV que contiene datos sensibles (p. ej. edad, estado civil, nacionalidad), **When**
   se calcula el score, **Then** esos atributos no influyen en el score y el sistema lo refleja.
6. **Given** un archivo que no es PDF/DOCX o está corrupto/ilegible, **When** el recruiter lo sube,
   **Then** el sistema responde con un error claro y no genera un dossier inválido.

---

### User Story 3 - Recruiter revisa el dossier y registra la decisión humana final (Priority: P2)

El recruiter revisa el dossier completo (resumen, skills con evidencia, brechas, inconsistencias
neutrales, preguntas de entrevista, recomendación no vinculante) y registra su decisión final sobre
el candidato — entrevistar, revisar o descartar — con una nota opcional. La recomendación de la IA
nunca decide por sí sola; la decisión la toma y firma el humano, y queda en el registro de auditoría.

**Why this priority**: Cierra el ciclo con accountability humano (principio no negociable) y produce
la traza de decisión que diferencia al producto. Depende de que exista un dossier (US2).

**Independent Test**: Sobre un dossier existente, registrar cada tipo de decisión y verificar que se
persiste con actor, fecha/hora, la recomendación de IA mostrada y el resultado humano, y que aparece
en el audit log.

**Acceptance Scenarios**:

1. **Given** un dossier generado, **When** el recruiter registra una decisión (entrevistar / revisar
   / descartar) con nota opcional, **Then** la decisión se guarda con actor, timestamp, la
   recomendación de IA mostrada y el resultado humano.
2. **Given** un dossier generado, **When** el sistema lo presenta, **Then** en ningún momento marca al
   candidato como rechazado/avanzado de forma automática: el estado final solo cambia por acción
   humana.
3. **Given** una decisión registrada, **When** se consulta el registro de auditoría de la
   organización, **Then** aparece un evento `decision_recorded` asociado al candidato y al recruiter.

---

### User Story 4 - Recruiter exporta el dossier a PDF (Priority: P3)

El recruiter exporta el dossier del candidato a un archivo PDF para compartirlo con el equipo de
contratación o archivarlo, conservando el score, su desglose, las evidencias, las inconsistencias,
las preguntas de entrevista y la decisión registrada.

**Why this priority**: Aumenta la vendibilidad y la utilidad práctica, pero no es imprescindible para
validar el valor central; por eso es P3. Depende del dossier (US2) y, si existe, incluye la decisión
(US3).

**Independent Test**: Sobre un dossier existente, solicitar la exportación y verificar que se produce
un PDF que contiene las secciones del dossier y que la acción queda registrada.

**Acceptance Scenarios**:

1. **Given** un dossier generado, **When** el recruiter solicita exportarlo, **Then** el sistema
   produce un PDF con el resumen, score y desglose, skills con evidencia, brechas, inconsistencias,
   preguntas de entrevista y (si existe) la decisión registrada.
2. **Given** una exportación realizada, **When** se consulta el audit log, **Then** aparece un evento
   `pdf_exported`.

---

### Edge Cases

- **CV ilegible o escaneado como imagen sin texto**: el sistema informa que no pudo extraer texto y no
  genera un dossier basado en datos vacíos (OCR queda fuera de alcance Fase 1).
- **CV en idioma distinto al esperado**: el sistema procesa el texto disponible y, si la cobertura de
  evidencia es baja, lo refleja como menor confianza, sin inventar datos.
- **Skill declarada en el CV pero sin evidencia que la respalde**: aparece con confianza baja o como
  inconsistencia "requiere revisión", nunca afirmada como verificada.
- **Vacante sin skills deseables o sin rango salarial**: el score se calcula con los factores
  disponibles y el desglose indica qué factores no aplicaron, sin penalizar arbitrariamente.
- **Consentimiento declarado y luego retirado**: el candidato/recruiter puede solicitar el borrado de
  los datos del candidato; el sistema debe permitir eliminarlos.
- **Dossier solicitado sobre una vacante de otra organización**: rechazado por aislamiento multi-tenant.
- **Conclusión sin fuente disponible**: el sistema no la muestra como afirmación; toda conclusión
  mostrada debe tener evidencia (principio Evidence-Based Scoring).

## Requirements *(mandatory)*

### Functional Requirements

**Autenticación, organización y permisos**

- **FR-001**: El sistema MUST autenticar usuarios y asociarlos a una organización (tenant).
- **FR-002**: El sistema MUST soportar los roles `org_admin`, `recruiter` y `viewer`, y aplicar sus
  permisos por operación (los `viewer` no crean vacantes ni registran decisiones).
- **FR-003**: El sistema MUST aislar todos los datos por organización: ninguna operación puede
  devolver o afectar datos de otra organización.

**Vacantes**

- **FR-004**: Los recruiters MUST poder crear una vacante con título, descripción, skills
  obligatorias, skills deseables, modalidad, país/zona, rango salarial y seniority esperado.
- **FR-005**: El sistema MUST validar los campos obligatorios de la vacante y rechazar creaciones
  incompletas con mensajes claros.
- **FR-006**: Los recruiters MUST poder listar y consultar las vacantes de su organización.

**Carga de CV y consentimiento**

- **FR-007**: Los recruiters MUST poder subir el CV de un candidato asociado a una vacante,
  restringido a formato PDF o DOCX con texto extraíble y un tamaño máximo de 5 MB; el sistema MUST
  rechazar otros formatos, archivos mayores a 5 MB y PDFs escaneados como imagen (sin texto
  extraíble) con un error claro.
- **FR-008**: El sistema MUST capturar y versionar el consentimiento del candidato para el análisis
  antes de procesarlo, registrando qué se analizará y cuándo se otorgó.
- **FR-009**: El sistema MUST rechazar la generación del dossier si no existe consentimiento
  registrado.
- **FR-010**: El sistema MUST extraer del CV los datos estructurados relevantes (datos de contacto
  profesionales, educación, experiencia con fechas, skills, idiomas, certificaciones) y MUST manejar
  archivos ilegibles o de formato no soportado con un error claro, sin generar un dossier vacío.

**Scoring explicable y determinístico**

- **FR-011**: El sistema MUST calcular un score de compatibilidad candidato↔vacante en escala 0–100.
- **FR-012**: El score MUST ser determinístico y reproducible: el mismo CV y la misma vacante producen
  el mismo score y el mismo desglose.
- **FR-013**: El sistema MUST persistir un desglose por factor con pesos fijos que suman 100 —
  skills/stack obligatorias (35), experiencia relevante (20), seniority (15), modalidad/ubicación
  (10), evidencia/soporte (10) y penalización por inconsistencias (10) — cuyos componentes ponderados
  reconcilian con el score final. Cuando un factor no aplique por falta de datos en la vacante, el
  desglose MUST indicarlo sin penalizar arbitrariamente.
- **FR-014**: El LLM MUST NOT producir ni modificar el score numérico; solo puede generar texto que
  explique un score ya calculado.
- **FR-015**: El sistema MUST excluir del cálculo del score cualquier atributo sensible (edad, género,
  nacionalidad, estado civil, salud, religión, afiliación política, dirección exacta).

**Dossier**

- **FR-016**: El sistema MUST generar un resumen profesional del candidato basado en la evidencia del
  CV.
- **FR-017**: El sistema MUST listar las skills detectadas y, para cada conclusión relevante, MUST
  mostrar la fuente/evidencia que la respalda; no MUST mostrarse ninguna conclusión sin fuente.
- **FR-018**: El sistema MUST identificar brechas del candidato frente a los requisitos de la vacante.
- **FR-019**: El sistema MUST detectar, como mínimo, las siguientes señales de inconsistencia y
  presentarlas en lenguaje neutral ("requiere revisión"), sin formulaciones acusatorias: (a) fechas
  laborales solapadas o ilógicas, (b) gaps temporales grandes, (c) seniority declarado vs años de
  experiencia, (d) skill declarada sin evidencia en el cuerpo del CV, (e) idioma declarado vs idioma
  del CV, (f) educación incompleta o ambigua, y (g) certificaciones mencionadas sin detalle
  verificable.
- **FR-020**: El sistema MUST generar preguntas de entrevista sugeridas relacionadas con las skills,
  brechas e inconsistencias del candidato.
- **FR-021**: El sistema MUST presentar una recomendación explícitamente NO vinculante.

**Decisión humana**

- **FR-022**: Los recruiters MUST poder registrar la decisión humana final sobre un candidato
  (entrevistar / revisar / descartar) con una nota opcional.
- **FR-023**: El sistema MUST NOT marcar, rechazar, avanzar ni rankear a un candidato como resultado
  final de forma automática; el estado final solo cambia por acción humana.
- **FR-024**: Cada decisión MUST registrar el actor, el timestamp, la recomendación de IA mostrada y
  el resultado humano.

**Exportación**

- **FR-025**: Los recruiters MUST poder exportar el dossier a PDF, incluyendo score y desglose,
  evidencias, brechas, inconsistencias, preguntas de entrevista y la decisión registrada si existe.

**Auditoría, privacidad y trazabilidad**

- **FR-026**: El sistema MUST registrar en un audit log inmutable, como mínimo, los eventos
  `cv_parsed`, `dossier_generated`, `score_computed`, `decision_recorded` y `pdf_exported`, cada uno
  con actor, organización, objetivo y timestamp.
- **FR-027**: El sistema MUST permitir eliminar los datos de un candidato a solicitud (hard delete) y
  MUST soportar un período de retención por defecto configurable por variable de entorno (p. ej. 180
  días); la purga automática de datos vencidos no es obligatoria en la Fase 1.
- **FR-029**: El sistema MUST soportar CVs en español e inglés, optimizando el parseo y el dossier
  para español con tolerancia a contenido en inglés; la interfaz se presenta en español.
- **FR-028**: El sistema MUST NOT buscar antecedentes penales por nombre, MUST NOT scrapear datos
  sensibles de fuentes externas y MUST NOT fabricar conclusiones sin evidencia.

### Key Entities *(include if feature involves data)*

- **Organization**: el tenant. Agrupa usuarios, vacantes, candidatos, dossiers, decisiones y registros
  de auditoría. Todo dato pertenece a una organización.
- **User**: recruiter/admin/viewer perteneciente a una organización; tiene un rol que define permisos.
- **Vacancy**: el cargo a cubrir, con sus requisitos estructurados (skills obligatorias/deseables,
  modalidad, país, rango salarial, seniority). Referente del scoring.
- **Candidate**: la persona evaluada en el contexto de una vacante. En Fase 1 no tiene login; existe a
  partir del CV cargado por el recruiter.
- **CandidateDocument**: el archivo de CV (PDF/DOCX) cargado, con su contenido extraído y metadatos.
- **Consent**: el registro versionado del consentimiento del candidato para el análisis (qué, cuándo).
- **Dossier**: el resultado de la evaluación: resumen, skills con evidencia, brechas, inconsistencias,
  preguntas de entrevista, recomendación no vinculante. Asociado a un candidato y una vacante.
- **Score**: el resultado numérico 0–100 con su desglose por factor (reconciliable al total) y la
  narrativa explicativa generada por el LLM (que no altera el número).
- **Decision**: la decisión humana final (entrevistar/revisar/descartar) con actor, timestamp,
  recomendación de IA mostrada, resultado humano y nota.
- **AuditLogEntry**: registro inmutable de un evento relevante con actor, organización, objetivo,
  timestamp y metadatos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un recruiter puede pasar de "tengo un CV y una vacante" a "tengo un dossier con score y
  recomendación" en menos de 3 minutos por candidato.
- **SC-002**: El 100% de las conclusiones mostradas en el dossier tienen una fuente/evidencia asociada
  (cero afirmaciones sin fuente).
- **SC-003**: Para el mismo CV y la misma vacante, el score y su desglose son idénticos en el 100% de
  las ejecuciones repetidas.
- **SC-004**: En el 100% de los dossiers, los componentes ponderados del desglose reconcilian con el
  score final dentro del margen de redondeo.
- **SC-005**: Ningún candidato es marcado con un resultado final (rechazado/avanzado) sin una acción
  humana registrada (0 decisiones automáticas).
- **SC-006**: Los atributos sensibles no influyen en el score: alterar solo un atributo sensible del
  CV (p. ej. edad o estado civil) no cambia el score.
- **SC-007**: El 100% de las acciones relevantes (parseo de CV, generación de dossier, cálculo de
  score, decisión, exportación) quedan registradas en el audit log.
- **SC-008**: Un recruiter logra exportar un dossier a PDF completo y compartible en menos de 30
  segundos.

## Assumptions

- El candidato NO tiene login en la Fase 1; su consentimiento lo declara/captura el recruiter al
  cargar el CV y se guarda versionado.
- Se evalúa un candidato a la vez contra una vacante; el ranking masivo avanzado de muchos candidatos
  queda fuera de alcance de la Fase 1.
- El multi-tenant es técnico desde la Fase 1 (organizaciones y roles), pero sin billing, sin gestión
  avanzada de equipos ni facturación.
- Solo se soportan CVs con texto extraíble en PDF/DOCX; los CVs escaneados como imagen (OCR) quedan
  fuera de alcance de la Fase 1.
- La evaluación se basa únicamente en el CV cargado y la vacante; NO hay enriquecimiento desde
  LinkedIn/GitHub/portfolio ni fuentes externas en la Fase 1.
- Las verificaciones sensibles / antecedentes y las integraciones con proveedores de background check
  o ATS quedan explícitamente fuera de alcance de la Fase 1.
- El idioma principal de los CVs y de la interfaz es español, con tolerancia a CVs con contenido en
  inglés.
- La determinación reproducible del score se valida con el proveedor de IA simulado (mock) por
  defecto; el comportamiento con proveedores reales puede variar en la redacción de la narrativa, pero
  no en el número del score.

## Out of Scope (Phase 1)

Los siguientes elementos están explícitamente fuera del alcance de esta fase y NO deben implementarse
aquí: scraping de LinkedIn/GitHub/portfolio, Evidence Graph multi-fuente, portal de candidato con
login propio, Sensitive Check Gate / verificación de antecedentes, búsqueda de antecedentes penales,
integraciones con ATS, pagos/billing, extensión de navegador, y ranking masivo avanzado de múltiples
candidatos. Estas capacidades se consideran en fases posteriores.
