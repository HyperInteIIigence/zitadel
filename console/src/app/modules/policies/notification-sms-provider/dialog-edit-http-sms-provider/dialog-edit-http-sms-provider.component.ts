import { Component, Inject } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, ValidationErrors, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { UpdateSMSProviderHTTPRequest } from 'src/app/proto/generated/zitadel/admin_pb';
import { SMSProvider, SMSProviderConfigState } from 'src/app/proto/generated/zitadel/settings_pb';

const HYPERSMS_ORIGIN = 'https://intelligence.hyperit.net.au';
const HYPERSMS_PATH_PREFIX = '/__hypersms/';

/** Allow only the dedicated HTTPS HyperSMS ingress, not raw PlainApp GraphQL or arbitrary SSRF targets. */
export function hyperSmsEndpointValidator(control: AbstractControl): ValidationErrors | null {
  const value = String(control.value || '').trim();
  try {
    const parsed = new URL(value);
    if (
      parsed.origin !== HYPERSMS_ORIGIN ||
      !parsed.pathname.startsWith(HYPERSMS_PATH_PREFIX) ||
      parsed.username ||
      parsed.password ||
      parsed.search ||
      parsed.hash ||
      value !== parsed.href ||
      value.length > 2048
    ) {
      return { hyperSmsEndpoint: true };
    }
    return null;
  } catch {
    return { hyperSmsEndpoint: true };
  }
}

@Component({
  selector: 'cnsl-dialog-edit-http-sms-provider',
  templateUrl: './dialog-edit-http-sms-provider.component.html',
  standalone: false,
})
export class DialogEditHttpSmsProviderComponent {
  public readonly form = new FormGroup({
    description: new FormControl('', {
      nonNullable: true,
      validators: [Validators.maxLength(200)],
    }),
    endpoint: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, hyperSmsEndpointValidator],
    }),
  });
  public saving = false;
  public readonly active: boolean;

  constructor(
    public dialogRef: MatDialogRef<DialogEditHttpSmsProviderComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { provider: SMSProvider.AsObject },
  ) {
    this.active = data.provider.state === SMSProviderConfigState.SMS_PROVIDER_CONFIG_ACTIVE;
    this.form.setValue({
      description: data.provider.description || '',
      endpoint: data.provider.http?.endpoint || '',
    });
  }

  public save(): void {
    if (this.saving || this.active || this.form.invalid || !this.data.provider.id) {
      this.form.markAllAsTouched();
      return;
    }
    const req = new UpdateSMSProviderHTTPRequest();
    req.setId(this.data.provider.id);
    req.setDescription(this.form.controls.description.value.trim());
    req.setEndpoint(this.form.controls.endpoint.value.trim());
    this.dialogRef.close(req);
  }
}

