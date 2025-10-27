import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TalleresListadoComponent } from './listado.component';

describe('TalleresListadoComponent', () => {
    let component: TalleresListadoComponent;
    let fixture: ComponentFixture<TalleresListadoComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [TalleresListadoComponent],
        }).compileComponents();

        fixture = TestBed.createComponent(TalleresListadoComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
