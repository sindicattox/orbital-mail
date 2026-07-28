import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


logger = logging.getLogger(__name__)


FIELD_LABELS = {
    'associative_code': 'Situação associativa',
    'batch_size': 'Tamanho do lote',
    'body_html': 'Conteúdo HTML',
    'body_text': 'Conteúdo em texto',
    'emails': 'Destinatários',
    'from_email': 'E-mail do remetente',
    'from_name': 'Nome do remetente',
    'functional_code': 'Situação funcional',
    'internal_name': 'Nome interno',
    'provider': 'Provedor',
    'repetitions': 'Envios por e-mail',
    'reply_to': 'Responder para',
    'sender_email': 'E-mail do remetente',
    'sender_name': 'Nome do remetente',
    'status': 'Status',
    'subject': 'Assunto',
    'to_email': 'E-mail do destinatário',
    'to_name': 'Nome do destinatário',
    'workers': 'Workers',
}


class ApiErrorMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message):
            nonlocal response_started
            if message['type'] == 'http.response.start':
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.error(
                'Unhandled API error on %s',
                scope.get('path', ''),
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            if response_started:
                raise
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={'detail': 'Não foi possível concluir a operação. Tente novamente em instantes.'},
            )
            await response(scope, receive, send)


def _field_name(error: dict) -> str:
    location = [item for item in error.get('loc', ()) if item not in {'body', 'query', 'path'}]
    field = str(location[-1]) if location else 'Dados informados'
    return FIELD_LABELS.get(field, field.replace('_', ' ').capitalize())


def _validation_message(error: dict) -> str:
    field = _field_name(error)
    error_type = str(error.get('type') or '')
    context = error.get('ctx') or {}

    if error_type == 'missing':
        return f'{field} é obrigatório.'
    if error_type == 'string_too_short':
        return f'{field} deve ter pelo menos {context.get("min_length")} caracteres.'
    if error_type == 'string_too_long':
        return f'{field} deve ter no máximo {context.get("max_length")} caracteres.'
    if error_type in {'greater_than_equal', 'greater_than'}:
        limit = context.get('ge', context.get('gt'))
        return f'{field} deve ser maior ou igual a {limit}.'
    if error_type in {'less_than_equal', 'less_than'}:
        limit = context.get('le', context.get('lt'))
        return f'{field} deve ser menor ou igual a {limit}.'
    if error_type in {'enum', 'string_pattern_mismatch', 'int_parsing', 'float_parsing'}:
        return f'{field} possui um valor inválido.'
    if 'email' in field.lower() and error_type == 'value_error':
        return f'{field} deve conter um endereço válido.'

    message = str(error.get('msg') or '').removeprefix('Value error, ').strip()
    if message:
        return message if message.endswith(('.', '!', '?')) else f'{message}.'
    return 'Revise os dados informados.'


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    detail = _validation_message(errors[0]) if errors else 'Revise os dados informados.'
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={'detail': detail})


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning(
        'Database integrity error on %s',
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    message = str(getattr(exc, 'orig', exc))
    if 'ORA-00001' in message:
        detail = 'Não foi possível salvar porque já existe um registro com os mesmos dados.'
    elif 'ORA-01400' in message:
        detail = 'Não foi possível salvar porque um campo obrigatório não foi informado.'
    elif 'ORA-02291' in message:
        detail = 'Não foi possível salvar porque um registro relacionado não foi encontrado.'
    elif 'ORA-02292' in message:
        detail = 'Não foi possível remover porque existem registros relacionados.'
    else:
        detail = 'Não foi possível concluir a operação devido a uma regra do banco de dados.'
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={'detail': detail})


async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(
        'Database error on %s',
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={'detail': 'Não foi possível acessar o banco de dados. Tente novamente em instantes.'},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_middleware(ApiErrorMiddleware)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
