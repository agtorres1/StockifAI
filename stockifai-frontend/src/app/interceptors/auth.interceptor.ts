import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Clonar request y agregar withCredentials para enviar cookies
    const clonedRequest = req.clone({
      withCredentials: true  // ← Envía cookies de sesión en cada request
    });

    return next.handle(clonedRequest);
  }
}
