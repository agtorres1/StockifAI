import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
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
import { TalleresUsuariosComponent } from './features/talleres/usuarios/usuarios.component';
import { RegisterComponent } from './session/register/register.component';
import { AuthLayoutComponent } from './layout/auth-layout/auth-layout.component';
import { LayoutComponent } from './layout/layout.component';
import { LoginComponent } from './session/login/login.component';

export const routes: Routes = [
  // Rutas de autenticación (SIN sidebar)
  {
    path: 'auth',
    component: AuthLayoutComponent,
    children: [
      { path: 'login', component: LoginComponent },
      { path: 'register', component: RegisterComponent }
    ]
  },

  // Rutas principales (CON sidebar)
  {
    path: '',
    component: LayoutComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: DashboardComponent },
      { path: 'alertas', component: AlertasComponent },

      // Talleres
      {
        path: 'talleres',
        children: [
          { path: 'listado', component: TalleresListadoComponent },
          { path: 'grupos', component: TalleresGruposComponent },
          { path: 'usuarios', component: TalleresUsuariosComponent },
        ]
      },

      // Repuestos
      {
        path: 'repuestos',
        children: [
          { path: 'movimientos', component: MovimientosComponent },
          { path: 'forecasting', component: ForecastingComponent },
          { path: 'stock', component: StockComponent },
          { path: 'catalogo', component: CatalogoComponent },
          { path: 'marcas', component: MarcasComponent },
          { path: 'categorias', component: CategoriasComponent },
          { path: 'localizador', component: LocalizadorComponent },
        ]
      },
    ]
  },

  // Catch-all
  { path: '**', redirectTo: 'dashboard' }
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule],
})
export class AppRoutingModule {}
