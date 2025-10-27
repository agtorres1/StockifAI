import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SemaforoAlertasComponent } from './semaforo-alertas.component';

describe('SemaforoAlertasComponent', () => {
    let component: SemaforoAlertasComponent;
    let fixture: ComponentFixture<SemaforoAlertasComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [SemaforoAlertasComponent],
        }).compileComponents();

        fixture = TestBed.createComponent(SemaforoAlertasComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
