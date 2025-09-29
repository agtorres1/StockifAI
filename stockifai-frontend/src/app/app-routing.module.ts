import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { ForecastingComponent } from './features/repuestos/forecasting/forecasting.component';
import { MovimientosComponent } from './features/repuestos/movimientos/movimientos.component';
import { StockComponent } from './features/repuestos/stock/stock.component';
import { TalleresGruposComponent } from './features/talleres/grupos/grupos.component';
import { TalleresListadoComponent } from './features/talleres/listado/listado.component';
import { TalleresUsuariosComponent } from './features/talleres/usuarios/usuarios.component';
import { CatalogoComponent } from './features/repuestos/catalogo/catalogo.component';
import { MarcasComponent } from './features/repuestos/marcas/marcas.component';
import { CategoriasComponent } from './features/repuestos/categorias/categorias.component';
import { LocalizadorComponent } from './features/repuestos/localizador/localizador.component';

const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'talleres', children: [
    { path: 'listado', component: TalleresListadoComponent },
    { path: 'grupos', component: TalleresGruposComponent },
    { path: 'usuarios', component: TalleresUsuariosComponent },
  ]},
  { path: 'repuestos', children: [
    { path: 'movimientos', component: MovimientosComponent },
    { path: 'forecasting', component: ForecastingComponent },
    { path: 'stock', component: StockComponent },
    { path: 'catalogo', component: CatalogoComponent },
    { path: 'marcas', component: MarcasComponent },
    { path: 'categorias', component: CategoriasComponent },
    { path: 'localizador', component: LocalizadorComponent },

  ]},
  { path: '**', redirectTo: 'dashboard' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
