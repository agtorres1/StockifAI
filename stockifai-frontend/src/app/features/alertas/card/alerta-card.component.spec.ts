import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlertaCardComponent } from './alerta-card.component';

describe('AlertasComponent', () => {
    let component: AlertaCardComponent;
    let fixture: ComponentFixture<AlertaCardComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [AlertaCardComponent],
        }).compileComponents();

        fixture = TestBed.createComponent(AlertaCardComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
