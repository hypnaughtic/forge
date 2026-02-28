# Django Fullstack Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

A fullstack Python web application using Django with Django REST Framework for API endpoints and Celery for asynchronous task processing. Follows Django best practices with a modular app structure.

## What a Full Scaffold Would Provide

- **Django project** with modular app structure and settings split by environment
- **Django REST Framework** with serializers, viewsets, and permission classes
- **Celery integration** with Redis/RabbitMQ broker and periodic task scheduling
- **Authentication** with JWT tokens (djangorestframework-simplejwt)
- **Database migrations** with Django ORM and PostgreSQL
- **Admin interface** with customized ModelAdmin classes
- **API documentation** with drf-spectacular (OpenAPI 3.0)
- **CORS and security** middleware configuration
- **Static file handling** with whitenoise for production
- **Testing** with pytest-django and factory_boy
- **Docker Compose** stack with web, worker, beat, Redis, and PostgreSQL
- **Management commands** for common operations

## Key Technologies

| Component       | Technology               |
|----------------|--------------------------|
| Framework       | Django 5.x               |
| API             | Django REST Framework    |
| Task Queue      | Celery                   |
| Database        | PostgreSQL               |
| Broker          | Redis                    |
| Testing         | pytest-django            |
