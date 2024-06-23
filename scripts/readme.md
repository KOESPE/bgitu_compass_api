# Используемые в работе скрипты
Для корректной работе на сервере используется несколько скриптов.

## supervisord
Менеджер процессов. Удобнее в использовании чем systemd. 
В файле supervisord.conf указан скрипт для работы с gunicorn

Для запуска используются команда
`sudo supervisorctl start compass-api`

Для проверки статуса и логов
`sudo supervisorctl status` и `sudo supervisorctl tail -f compass-api`

## gunicorn
WSGI Python сервер, продакшн версия uvicorn, параметры запуска указаны в <u>start_gunicorn</u>

## Nginx

Ключевая строчка — <u>upstream app_server</u>, где далее указан путь до сокета, что опредлен в <u>start_gunicorn</u>