import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { DEFAULT_CURRENCY_CODE, LOCALE_ID, NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AlertaCardComponent } from './features/alertas/card/alerta-card.component';
import { AlertasComponent } from './features/alertas/listado/alertas.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { CatalogoComponent } from './features/repuestos/catalogo/catalogo.component';
import { CategoriasComponent } from './features/repuestos/categorias/categorias.component';
import { ForecastingComponent } from './features/repuestos/forecasting/forecasting.component';
import { LocalizadorComponent } from './features/repuestos/localizador/localizador.component';
import { MarcasComponent } from './features/repuestos/marcas/marcas.component';
import { MovimientosComponent } from './features/repuestos/movimientos/movimientos.component';
import { StockComponent } from './features/repuestos/stock/stock.component';
import { TalleresGruposComponent } from './features/talleres/grupos/grupos.component';
import { TalleresListadoComponent } from './features/talleres/listado/listado.component';
import { EditUsuarioComponent } from './features/talleres/usuarios/edit/edit-usuario.component';
import { TalleresUsuariosComponent } from './features/talleres/usuarios/usuarios.component';
import { LayoutComponent } from './layout/layout.component';
import { SharedModule } from './shared/shared.module';
import { RegisterComponent } from './session/register/register.component';
import { AuthLayoutComponent } from './layout/auth-layout/auth-layout.component';
import { LoginComponent } from './session/login/login.component';

import { registerLocaleData } from '@angular/common';
import localeEsAr from '@angular/common/locales/es-AR';

registerLocaleData(localeEsAr, 'es-AR');

@NgModule({
    declarations: [
        AppComponent,
        LayoutComponent,
        DashboardComponent,
        StockComponent,
        ForecastingComponent,
        MovimientosComponent,
        TalleresGruposComponent,
        TalleresListadoComponent,
        TalleresUsuariosComponent,
        CatalogoComponent,
        MarcasComponent,
        CategoriasComponent,
        LocalizadorComponent,
        AuthLayoutComponent,
        RegisterComponent,
        LoginComponent,
        EditUsuarioComponent,
        AlertasComponent,
        AlertaCardComponent,
    ],
    imports: [
        BrowserModule,
        CommonModule,
        RouterModule.forRoot([]),
        AppRoutingModule,
        FormsModule,
        ReactiveFormsModule,
        HttpClientModule,
        BaseChartDirective,
        SharedModule,
        RouterModule,
    ],
    providers: [
        provideCharts(withDefaultRegisterables()),
        { provide: LOCALE_ID, useValue: 'es-AR' },
        { provide: DEFAULT_CURRENCY_CODE, useValue: '$' },
    ],
    bootstrap: [AppComponent],
})
export class AppModule {}
