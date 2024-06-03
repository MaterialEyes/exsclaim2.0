from transformers import AutoProcessor, BlipForConditionalGeneration, Blip2ForConditionalGeneration
from datasets import load_dataset
from torch.utils.data import Dataset, DataLoader
from peft import LoraConfig, get_peft_model
import torch
import os

dataset = load_dataset("kvriza8/microscopy_images", split="train")
processor = AutoProcessor.from_pretrained("Salesforce/blip2-opt-2.7b")
model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b", device_map="auto")


# Define the LoraConfig
config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    target_modules=["q_proj", "k_proj"]
)


class ImageCaptioningDataset(Dataset):
    def __init__(self, dataset, processor):
        self.dataset = dataset
        self.processor = processor

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        item = self.dataset[idx]
        encoding = self.processor(images=item["image"], padding="max_length", return_tensors="pt")
        # remove batch dimension
        encoding = {k: v.squeeze() for k, v in encoding.items()}
        encoding["caption_summary"] = item["caption_summary"]
        return encoding


def collate_fn(batch):
    # pad the input_ids and attention_mask
    processed_batch = {}
    for key in batch[0].keys():
        if key != "caption_summary":
            processed_batch[key] = torch.stack([example[key] for example in batch])
        else:
            text_inputs = processor.tokenizer(
                [example["caption_summary"] for example in batch], padding=True, return_tensors="pt"
            )
            processed_batch["input_ids"] = text_inputs["input_ids"]
            processed_batch["attention_mask"] = text_inputs["attention_mask"]
    return processed_batch
    

def find_latest_checkpoint(checkpoint_dir):
    checkpoint_paths = [os.path.join(checkpoint_dir, f) for f in os.listdir(checkpoint_dir) if f.endswith('.pth')]
    if not checkpoint_paths:
        return None
    latest_checkpoint = max(checkpoint_paths, key=os.path.getctime)
    return latest_checkpoint
    

def save_checkpoint(epoch, model, optimizer, loss, checkpoint_dir="checkpoints"):
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    checkpoint_path = os.path.join(checkpoint_dir, f"checkpoint_epoch_{epoch}_loss_{loss:.4f}.pth")
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
    }, checkpoint_path)
    print(f"Checkpoint saved to {checkpoint_path}")


if __name__ == "__main__":
    # Initialize a list to keep track of loss history
    loss_history = []
    optimizer = torch.optim.Adam(model.parameters(), lr=5e-4)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Specify your checkpoint directory
    checkpoint_dir = "checkpoints_full_captions"

    # Attempt to find and load the latest checkpoint
    latest_checkpoint_path = find_latest_checkpoint(checkpoint_dir)
    if latest_checkpoint_path:
        print(f"Found latest checkpoint: {latest_checkpoint_path}")
        start_epoch, loss_history = load_checkpoint(latest_checkpoint_path, model, optimizer)
        print(f"Resuming training from epoch {start_epoch + 1}")
    else:
        print("No checkpoint found, starting training from scratch")
        start_epoch = 0
        loss_history = []

    # Ensure the model is on the correct device
    model.to(device)
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    checkpoint = torch.load(latest_checkpoint_path)
    model_state_dict = checkpoint['model_state_dict']

    # Load the model state dictionary into the model
    model.load_state_dict(model_state_dict)
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

    train_dataset = ImageCaptioningDataset(dataset, processor)
    train_dataloader = DataLoader(train_dataset, shuffle=True, batch_size=4, collate_fn=collate_fn)
    model.train()
    # Your training loop
    accumulation_steps = 4  # Number of steps to accumulate gradients before updating model parameters
    EPOCH = 20
    for epoch in range(EPOCH):
        print("Epoch:", epoch)
        total_loss = 0.0
        for idx, batch in enumerate(train_dataloader):
            input_ids = batch.pop("input_ids").to(device)
            pixel_values = batch.pop("pixel_values").to(device, torch.float16)

            outputs = model(input_ids=input_ids, pixel_values=pixel_values, labels=input_ids)

            loss = outputs.loss
            total_loss += loss.item()

            print("Loss:", loss.item())

            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

        # Save checkpoint at the end of each epoch
        average_loss = total_loss / len(train_dataloader)
        save_checkpoint(epoch, model, optimizer, average_loss)

    # Set your API key as an environment variable
    os.environ["HF_API_KEY"] = "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"

    # Then use it in the push_to_hub call
    # model.push_to_hub("kvriza8/blip2-microscopy-captions", use_auth_token=os.environ["HF_API_KEY"])
    model.push_to_hub("kvriza8/blip2-opt-2.7b-microscopy-20-epoch-caption_summary", use_auth_token=os.environ["HF_API_KEY"])
