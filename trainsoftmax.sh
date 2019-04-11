#!/bin/bash 
echo "train softmax"

# input datasets directory
ds=~
echo "datasets directory" ${ds}

# output logs and models directories
md=~
echo "output directory" ${md}

python3 -m facenet.train_softmax \
    --model_def facenet.models.inception_resnet_v1 \
    --data_dir ${ds}/datasets/vggface2/train_mtcnn_182 \
    --image_size 160 \
    --lfw_dir ${ds}/datasets/lfw_mtcnnalign_160 \
    --models_base_dir ${md}/models/facenet \
    --pretrained_model ${md}/models/facenet/softmax/pretrained_inception_resnet_v1/model-20190327-175738.ckpt-275 \
    --learning_rate_schedule_file learning_rate_schedule_classifier_vggface2.txt \
    --optimizer ADAM \
    --learning_rate -1 \
    --max_nrof_epochs 500 \
    --batch_size 90 \
    --keep_probability 0.4 \
    --random_rotate \
    --random_flip \
    --use_fixed_image_standardization \
    --weight_decay 5e-4 \
    --embedding_size 512 \
    --lfw_distance_metric 1 \
    --lfw_use_flipped_images \
    --lfw_subtract_mean \
    --validation_set_split_ratio 0.01 \
    --validate_every_n_epochs 5
