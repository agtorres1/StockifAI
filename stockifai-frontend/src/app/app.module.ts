import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { CatalogoComponent } from './features/repuestos/catalogo/catalogo.component';
import { CategoriasComponent } from './features/repuestos/categorias/categorias.component';
import { ForecastingComponent } from './features/repuestos/forecasting/forecasting.component';
import { MarcasComponent } from './features/repuestos/marcas/marcas.component';
import { MovimientosComponent } from './features/repuestos/movimientos/movimientos.component';
import { StockComponent } from './features/repuestos/stock/stock.component';
import { TalleresGruposComponent } from './features/talleres/grupos/grupos.component';
import { TalleresListadoComponent } from './features/talleres/listado/listado.component';
import { TalleresUsuariosComponent } from './features/talleres/usuarios/usuarios.component';
import { LayoutComponent } from './layout/layout.component';
import { SharedModule } from './shared/shared.module';
import { LocalizadorComponent } from './features/repuestos/localizador/localizador.component';
import { RegisterComponent } from './session/register/register.component';
import { AuthLayoutComponent } from './layout/auth-layout/auth-layout.component';
import { ReactiveFormsModule } from '@angular/forms';
import { LoginComponent } from './session/login/login.component';

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
        LoginComponent

    ],
    imports: [
        BrowserModule,
        CommonModule,
        RouterModule.forRoot([]),
        AppRoutingModule,
        FormsModule,
        HttpClientModule,
        BaseChartDirective,
        SharedModule,
        RouterModule,
        ReactiveFormsModule

    ],
    providers: [provideCharts(withDefaultRegisterables())],
    bootstrap: [AppComponent],
})
export class AppModule {}
